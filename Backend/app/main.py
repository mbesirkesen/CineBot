"""FastAPI application entrypoint, lifespan management, CORS, and API routes."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    FilterOptions,
    HealthResponse,
    MovieItem,
)
from app.services.dataset import MovieDatasetService
from app.services.llm import LLMService, factual_follow_up, is_follow_up_question
from app.services.recommendation import RecommendationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("cinebot")

settings = get_settings()
dataset_service = MovieDatasetService(settings)
recommendation_service = RecommendationService(settings, dataset_service)
llm_service = LLMService(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize dataset, embedding model, and FAISS index on server startup."""
    logger.info("Starting %s in %s mode...", settings.app_name, settings.app_env)
    await asyncio.to_thread(recommendation_service.initialize)
    logger.info(
        "CineBot ready! Indexed %d movies | Active LLM provider: %s",
        recommendation_service.total_movies,
        llm_service.active_provider,
    )
    yield
    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "Movie recommendation chatbot API powered by "
        "HuggingFace Datasets, a multilingual SentenceTransformer, FAISS, and Groq."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Return server readiness, indexed movie count, and active model configuration."""
    return HealthResponse(
        status="ok" if recommendation_service.is_ready else "initializing",
        app_name=settings.app_name,
        dataset_loaded=recommendation_service.is_ready,
        total_movies=recommendation_service.total_movies,
        embedding_model=settings.embedding_model_name,
        llm_provider=llm_service.active_provider,
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat & Recommendations"])
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """Process a user message, retrieve semantic movie matches via FAISS, and generate an LLM reply."""
    start_time = time.perf_counter()

    previous = payload.previous_recommendations
    follow_up = is_follow_up_question(payload.message, previous)

    try:
        if follow_up:
            # The user is asking about the films already on screen; keep them and skip the vector search.
            recommendations = await llm_service.translate_overviews(previous)
            expanded_query = payload.message
        else:
            recommendations, expanded_query = await asyncio.to_thread(
                recommendation_service.search,
                payload.message,
                payload.top_k,
                payload.filters,
            )
            recommendations = await llm_service.translate_overviews(recommendations)

        factual = factual_follow_up(payload.message, recommendations) if follow_up else None
        if factual:
            reply, provider_used = factual, "katalog"
        else:
            reply, provider_used = await llm_service.generate_response(
                user_message=payload.message,
                movies=recommendations,
                history=payload.history,
                catalog=recommendation_service.catalog_titles(),
                previous=previous,
                follow_up=follow_up,
            )
    except Exception as exc:
        logger.exception("Error processing chat request: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Öneri oluşturulurken bir hata meydana geldi: {exc}",
        ) from exc

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return ChatResponse(
        reply=reply,
        recommendations=recommendations,
        query_used=expanded_query,
        llm_provider=provider_used,
        latency_ms=latency_ms,
        follow_up=follow_up,
    )


@app.get(
    "/api/recommend",
    response_model=list[MovieItem],
    tags=["Chat & Recommendations"],
)
async def semantic_search_endpoint(
    q: str = Query(..., min_length=1, description="Search query for semantic movie retrieval"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    genre: Optional[str] = Query(default=None, description="Optional genre filter"),
    min_rating: Optional[float] = Query(default=None, ge=0.0, le=10.0, description="Minimum TMDB rating"),
    min_year: Optional[int] = Query(default=None, ge=1900, le=2030, description="Minimum release year"),
) -> list[MovieItem]:
    """Direct semantic search endpoint without LLM generation."""
    filters = FilterOptions(genre=genre, min_rating=min_rating, min_year=min_year)
    recommendations, _ = await asyncio.to_thread(
        recommendation_service.search,
        q,
        top_k,
        filters,
    )
    return recommendations
