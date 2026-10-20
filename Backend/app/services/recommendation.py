"""FAISS vector store and semantic search engine using SentenceTransformers."""

from __future__ import annotations

import logging
import math
from typing import Any

import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer

from app.config import Settings, get_settings
from app.schemas.chat import FilterOptions, MovieItem
from app.services.dataset import MovieDatasetService

logger = logging.getLogger(__name__)

# Bilingual Turkish -> English semantic expansion dictionary so Turkish queries
# retrieve accurate results even on English TMDB movie descriptions.
TR_TO_EN_CONCEPTS: dict[str, str] = {
    "bilim kurgu": "science fiction sci-fi space future dystopia technology",
    "aksiyon": "action fight adventure explosive hero",
    "gerilim": "thriller suspense tension mystery psychological",
    "korku": "horror scary supernatural ghost monster slasher",
    "komedi": "comedy funny humor laugh romantic comedy",
    "dram": "drama emotional life family tragedy",
    "romantik": "romance love relationship emotional",
    "suç": "crime detective mafia heist police murder",
    "gizem": "mystery detective investigation puzzle whodunit",
    "animasyon": "animation animated family studio ghibli pixar",
    "fantastik": "fantasy magic mythical adventure supernatural",
    "macera": "adventure journey exploration quest survival",
    "savaş": "war military battle soldiers historical",
    "tarih": "history historical period biography",
    "uzay": "space interstellar astronaut galaxy planet alien",
    "zaman yolculuğu": "time travel paradox future past timeline",
    "zihin bükücü": "mind-bending psychological twist dream reality subconscious",
    "psikolojik": "psychological mind thriller twist insanity",
    "yapay zeka": "artificial intelligence AI robot cybernetics future",
    "distopya": "dystopian post-apocalyptic survival totalitarian future",
    "seri katil": "serial killer detective murder investigation crime",
    "soygun": "heist bank robbery crime clever plan",
    "intikam": "revenge vengeance justice payback",
    "aile": "family heartwarming children parents",
    "müzik": "music musician concert band passion",
}


class RecommendationService:
    """Manages SentenceTransformers embeddings and FAISS cosine similarity search."""

    def __init__(
        self,
        settings: Settings | None = None,
        dataset_service: MovieDatasetService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.dataset_service = dataset_service or MovieDatasetService(self.settings)
        self.df: pd.DataFrame = pd.DataFrame()
        self.model: SentenceTransformer | None = None
        self.index: faiss.IndexFlatIP | None = None
        self._is_ready: bool = False
        self._catalog_cache: list[tuple[str, int | None]] | None = None

    @property
    def is_ready(self) -> bool:
        """Whether the dataset, embedding model, and FAISS index are initialized."""
        return self._is_ready and not self.df.empty and self.index is not None

    @property
    def total_movies(self) -> int:
        """Total number of indexed movies."""
        return len(self.df) if not self.df.empty else 0

    def catalog_titles(self) -> list[tuple[str, int | None]]:
        """Every indexed title, used to reject movie names the model was not given."""
        if self._catalog_cache is not None:
            return self._catalog_cache
        if self.df.empty or "title" not in self.df.columns:
            return []

        years = self.df["release_year"] if "release_year" in self.df.columns else [None] * len(self.df)
        year_values = years.tolist() if hasattr(years, "tolist") else list(years)
        titles: list[tuple[str, int | None]] = []
        for title, year in zip(self.df["title"].tolist(), year_values):
            if not isinstance(title, str) or not title.strip():
                continue
            parsed: int | None = None
            if year is not None and not (isinstance(year, float) and math.isnan(year)):
                try:
                    parsed = int(year)
                except (TypeError, ValueError):
                    parsed = None
            titles.append((title.strip(), parsed))
        self._catalog_cache = titles
        return titles

    def initialize(self, force_rebuild: bool = False) -> None:
        """Load dataset, initialize SentenceTransformer, and build or load FAISS index."""
        logger.info("Initializing RecommendationService...")
        self.df = self.dataset_service.load_or_create_dataset(force_refresh=force_rebuild)
        self._catalog_cache = None

        logger.info("Loading SentenceTransformer model: %s", self.settings.embedding_model_name)
        self.model = SentenceTransformer(self.settings.embedding_model_name)

        index_path = self.settings.faiss_index_path
        if index_path.exists() and not force_rebuild:
            try:
                loaded_index = faiss.read_index(str(index_path))
                if loaded_index.ntotal == len(self.df):
                    self.index = loaded_index
                    self._is_ready = True
                    logger.info(
                        "Loaded cached FAISS index with %d vectors from %s",
                        self.index.ntotal,
                        index_path,
                    )
                    return
                logger.info(
                    "Cached FAISS index count (%d) != dataset size (%d). Rebuilding index.",
                    loaded_index.ntotal,
                    len(self.df),
                )
            except Exception as exc:
                logger.warning("Failed to read cached FAISS index (%s). Rebuilding.", exc)

        self._build_faiss_index()
        self._is_ready = True

    def _build_faiss_index(self) -> None:
        """Encode movie descriptions and build a normalized Inner Product (Cosine) FAISS index."""
        if self.model is None or self.df.empty:
            raise RuntimeError("Model and dataset must be loaded before building FAISS index.")

        texts = self.df["search_text"].fillna("").astype(str).tolist()
        logger.info("Encoding %d movie records with '%s'...", len(texts), self.settings.embedding_model_name)

        embeddings = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        self.index = index

        try:
            faiss.write_index(index, str(self.settings.faiss_index_path))
            logger.info("Saved FAISS index (%d vectors, dim=%d) to %s", index.ntotal, dimension, self.settings.faiss_index_path)
        except Exception as exc:
            logger.warning("Could not persist FAISS index to disk: %s", exc)

    @staticmethod
    def expand_bilingual_query(query: str) -> str:
        """Enrich Turkish queries with English semantic keywords for cross-lingual accuracy."""
        lowered = query.lower()
        expansions: list[str] = []
        for tr_term, en_keywords in TR_TO_EN_CONCEPTS.items():
            if tr_term in lowered:
                expansions.append(en_keywords)

        if expansions:
            return f"{query} | Related concepts: {' '.join(expansions)}"
        return query

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: FilterOptions | None = None,
    ) -> tuple[list[MovieItem], str]:
        """Perform semantic vector search over FAISS and apply optional metadata filters."""
        if not self.is_ready or self.model is None or self.index is None:
            self.initialize()

        assert self.model is not None and self.index is not None

        expanded_query = self.expand_bilingual_query(query)
        query_vector = self.model.encode(
            [expanded_query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        # Unfiltered search stays on the nearest neighbors. Active filters scan the
        # full catalog so a genre, rating, or year constraint is not dropped just
        # because the match sits outside the first 40 vectors.
        candidate_k = (
            len(self.df)
            if self._has_active_filters(filters)
            else min(max(top_k * 8, 40), len(self.df))
        )
        scores, indices = self.index.search(query_vector, candidate_k)

        results: list[MovieItem] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.df):
                continue

            row = self.df.iloc[int(idx)]
            movie = self._row_to_movie_item(row, float(score))

            if filters and not self._matches_filters(movie, filters):
                continue

            results.append(movie)
            if len(results) >= top_k:
                break

        return results, expanded_query

    @staticmethod
    def _has_active_filters(filters: FilterOptions | None) -> bool:
        """Return True when the request actually constrains genre, rating, or year."""
        if filters is None:
            return False
        return bool(filters.genre and filters.genre.strip()) or filters.min_rating is not None or filters.min_year is not None

    @staticmethod
    def _matches_filters(movie: MovieItem, filters: FilterOptions) -> bool:
        """Check whether a candidate movie satisfies user-provided metadata filters."""
        if filters.genre:
            target_genre = filters.genre.strip().lower()
            if not any(target_genre in g.lower() for g in movie.genres):
                return False

        if filters.min_rating is not None and movie.vote_average < filters.min_rating:
            return False

        if filters.min_year is not None:
            if movie.release_year is None or movie.release_year < filters.min_year:
                return False

        return True

    @staticmethod
    def _row_to_movie_item(row: pd.Series, score: float) -> MovieItem:
        """Convert a DataFrame row into a validated MovieItem schema."""
        raw_genres = str(row.get("genres", "Unknown"))
        genres = [g.strip() for g in raw_genres.split(",") if g.strip() and g.strip() != "Unknown"]

        raw_year: Any = row.get("release_year")
        release_year: int | None = None
        if raw_year is not None and not (isinstance(raw_year, float) and math.isnan(raw_year)):
            try:
                release_year = int(float(raw_year))
            except (ValueError, TypeError):
                release_year = None

        raw_date = row.get("release_date")
        release_date = (
            str(raw_date).strip()
            if raw_date is not None and not (isinstance(raw_date, float) and math.isnan(raw_date)) and str(raw_date).strip()
            else None
        )

        raw_poster = row.get("poster_url")
        poster_url = (
            str(raw_poster).strip()
            if raw_poster is not None and not (isinstance(raw_poster, float) and math.isnan(raw_poster)) and str(raw_poster).strip()
            else None
        )

        vote_avg = float(row.get("vote_average", 0.0) or 0.0)
        popularity = float(row.get("popularity", 0.0) or 0.0)

        return MovieItem(
            id=int(row.get("id", 0)),
            title=str(row.get("title", "Unknown")),
            overview=str(row.get("overview", "")),
            genres=genres,
            release_year=release_year,
            release_date=release_date,
            vote_average=round(vote_avg, 1),
            popularity=round(popularity, 2),
            poster_url=poster_url,
            similarity_score=round(max(0.0, min(1.0, score)), 4),
        )
