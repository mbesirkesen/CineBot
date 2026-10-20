"""Configuration management using Pydantic Settings v2."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App Info
    app_name: str = Field(default="CineBot API", description="Service name")
    app_env: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=True, description="Debug mode flag")

    # Server
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8000, description="Server bind port")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Dataset & Embeddings
    hf_dataset_name: str = Field(
        default="Ashaq2004/tmdb-movies",
        description="Primary HuggingFace dataset identifier",
    )
    hf_fallback_dataset_name: str = Field(
        default="Pablinho/movies-dataset",
        description="Fallback HuggingFace TMDB dataset identifier",
    )
    embedding_model_name: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="Multilingual SentenceTransformers model used for Turkish and English queries",
    )
    max_dataset_rows: int = Field(
        default=5000,
        ge=100,
        le=50000,
        description="Maximum number of movies to index in FAISS",
    )
    default_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Default number of movie recommendations to retrieve",
    )

    # Paths
    data_dir: Path = Field(default=DATA_DIR, description="Directory for local data storage")
    clean_csv_filename: str = Field(
        default="movies_clean.csv",
        description="Filename for cleaned movie dataset",
    )
    # LLM Settings
    llm_provider: Literal["groq", "gemini", "openai", "auto"] = Field(
        default="auto",
        description="LLM provider selection",
    )
    groq_api_key: str = Field(default="", description="Groq API Key")
    groq_model: str = Field(
        default="openai/gpt-oss-120b",
        description="Groq model name",
    )
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model name")
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model name")
    llm_temperature: float = Field(
        default=0.4,
        ge=0.0,
        le=1.5,
        description="Sampling temperature for LLM generation",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a clean list."""
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return origins or ["*"]

    @property
    def clean_csv_path(self) -> Path:
        """Full path to the cleaned movies CSV file."""
        return self.data_dir / self.clean_csv_filename

    @property
    def faiss_index_path(self) -> Path:
        """Full path to the cached FAISS vector index for the active embedding model."""
        slug = re.sub(r"[^a-z0-9]+", "-", self.embedding_model_name.lower()).strip("-")
        return self.data_dir / f"movies_{slug}.faiss"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
