"""Dataset loader & cleaner service for TMDB Movies from HuggingFace."""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Curated fallback seed data in case there is no internet access on first run
FALLBACK_MOVIES: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "Inception",
        "overview": "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: inception, the implantation of another person's idea into a target's subconscious.",
        "genres": "Action, Science Fiction, Adventure, Thriller",
        "release_date": "2010-07-15",
        "vote_average": 8.4,
        "popularity": 115.3,
        "poster_url": "https://image.tmdb.org/t/p/original/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
    },
    {
        "id": 2,
        "title": "Interstellar",
        "overview": "The adventures of a group of explorers who make use of a newly discovered wormhole to surpass the limitations on human space travel and conquer the vast distances involved in an interstellar voyage.",
        "genres": "Adventure, Drama, Science Fiction",
        "release_date": "2014-11-05",
        "vote_average": 8.6,
        "popularity": 140.2,
        "poster_url": "https://image.tmdb.org/t/p/original/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
    },
    {
        "id": 3,
        "title": "The Dark Knight",
        "overview": "Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets. The partnership proves to be effective, but they soon find themselves prey to a reign of chaos unleashed by a rising criminal mastermind known to the terrified citizens of Gotham as the Joker.",
        "genres": "Drama, Action, Crime, Thriller",
        "release_date": "2008-07-16",
        "vote_average": 8.5,
        "popularity": 130.5,
        "poster_url": "https://image.tmdb.org/t/p/original/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
    },
    {
        "id": 4,
        "title": "Parasite",
        "overview": "All unemployed, Ki-taek's family takes peculiar interest in the wealthy and glamorous Parks for their livelihood until they get entangled in an unexpected incident.",
        "genres": "Comedy, Thriller, Drama",
        "release_date": "2019-05-30",
        "vote_average": 8.5,
        "popularity": 95.4,
        "poster_url": "https://image.tmdb.org/t/p/original/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
    },
    {
        "id": 5,
        "title": "The Matrix",
        "overview": "Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.",
        "genres": "Action, Science Fiction",
        "release_date": "1999-03-30",
        "vote_average": 8.2,
        "popularity": 110.1,
        "poster_url": "https://image.tmdb.org/t/p/original/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
    },
    {
        "id": 6,
        "title": "Shutter Island",
        "overview": "World War II soldier-turned-U.S. Marshal Teddy Daniels investigates the disappearance of a patient from a hospital for the criminally insane, but his efforts are compromised by his troubling visions and also by a mysterious doctor.",
        "genres": "Drama, Thriller, Mystery",
        "release_date": "2010-02-14",
        "vote_average": 8.2,
        "popularity": 98.7,
        "poster_url": "https://image.tmdb.org/t/p/original/4GDy0PHYX3VRXUtwK5ysFbg3kEx.jpg",
    },
    {
        "id": 7,
        "title": "Arrival",
        "overview": "Taking place after alien crafts land around the world, an expert linguist is recruited by the military to determine whether they come in peace or are a threat.",
        "genres": "Drama, Science Fiction, Mystery",
        "release_date": "2016-11-10",
        "vote_average": 7.6,
        "popularity": 82.0,
        "poster_url": "https://image.tmdb.org/t/p/original/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
    },
    {
        "id": 8,
        "title": "Whiplash",
        "overview": "Under the direction of a ruthless instructor, a talented young drummer begins to pursue perfection at any cost, even his humanity.",
        "genres": "Drama, Music",
        "release_date": "2014-10-10",
        "vote_average": 8.4,
        "popularity": 88.9,
        "poster_url": "https://image.tmdb.org/t/p/original/7fn624j5lj3xTme2SgiLCeuedmO.jpg",
    },
    {
        "id": 9,
        "title": "Spirited Away",
        "overview": "A young girl, Chihiro, becomes trapped in a strange new world of spirits. When her parents undergo a mysterious transformation, she must call upon the courage she never knew she had to free her family.",
        "genres": "Animation, Family, Fantasy",
        "release_date": "2001-07-20",
        "vote_average": 8.5,
        "popularity": 102.3,
        "poster_url": "https://image.tmdb.org/t/p/original/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg",
    },
    {
        "id": 10,
        "title": "Se7en",
        "overview": "Two homicide detectives are on a desperate hunt for a serial killer whose crimes are based on the 'seven deadly sins' in this dark and haunting film that takes viewers from the tortured remains of one victim to the next.",
        "genres": "Crime, Mystery, Thriller",
        "release_date": "1995-09-22",
        "vote_average": 8.4,
        "popularity": 92.6,
        "poster_url": "https://image.tmdb.org/t/p/original/6yoghtyTpznpBik8EngEmJskVUO.jpg",
    },
    {
        "id": 11,
        "title": "Dune: Part Two",
        "overview": "Follow the mythic journey of Paul Atreides as he unites with Chani and the Fremen while on a path of revenge against the conspirators who destroyed his family.",
        "genres": "Science Fiction, Adventure, Action",
        "release_date": "2024-02-27",
        "vote_average": 8.3,
        "popularity": 165.0,
        "poster_url": "https://image.tmdb.org/t/p/original/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
    },
    {
        "id": 12,
        "title": "The Prestige",
        "overview": "A mysterious story of two magicians whose intense rivalry leads them on a life-long battle for supremacy -- full of obsession, deceit and jealousy with dangerous and deadly consequences.",
        "genres": "Drama, Mystery, Science Fiction, Thriller",
        "release_date": "2006-10-19",
        "vote_average": 8.2,
        "popularity": 85.1,
        "poster_url": "https://image.tmdb.org/t/p/original/tRNlZbgNCNOpLpbPEz5L8G8A0JN.jpg",
    },
]


class MovieDatasetService:
    """Service responsible for downloading, cleaning, and persisting TMDB movie data."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @staticmethod
    def _parse_genre_field(raw_value: Any) -> str:
        """Convert diverse genre formats (JSON list, Python list, or CSV string) to clean text."""
        if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
            return "Unknown"

        if isinstance(raw_value, list):
            names = [
                item.get("name", str(item)) if isinstance(item, dict) else str(item)
                for item in raw_value
            ]
            return ", ".join(filter(None, names)) or "Unknown"

        text = str(raw_value).strip()
        if not text:
            return "Unknown"

        if text.startswith("[") and text.endswith("]"):
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(text)
                    if isinstance(parsed, list):
                        names = [
                            item.get("name", str(item)) if isinstance(item, dict) else str(item)
                            for item in parsed
                        ]
                        cleaned = ", ".join(str(n).strip() for n in names if str(n).strip())
                        return cleaned or "Unknown"
                except (ValueError, SyntaxError, TypeError):
                    continue

        return text

    @staticmethod
    def _extract_year(date_str: Any) -> int | None:
        """Extract 4-digit release year from a date string."""
        if date_str is None or (isinstance(date_str, float) and pd.isna(date_str)):
            return None
        text = str(date_str).strip()
        if len(text) >= 4 and text[:4].isdigit():
            year = int(text[:4])
            if 1888 <= year <= 2035:
                return year
        return None

    def _normalize_dataframe(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize heterogeneous HuggingFace TMDB columns into a standard schema."""
        df = raw_df.copy()

        # Map case-insensitive column names
        col_map = {col.lower().strip(): col for col in df.columns}

        def pick_col(*candidates: str) -> pd.Series | None:
            for cand in candidates:
                if cand.lower() in col_map:
                    return df[col_map[cand.lower()]]
            return None

        title_series = pick_col("title", "original_title", "movie_title", "name")
        overview_series = pick_col("overview", "description", "plot", "synopsis", "tagline")
        genre_series = pick_col("genres", "genre", "listed_in")
        release_series = pick_col("release_date", "year", "first_air_date")
        vote_series = pick_col("vote_average", "rating", "imdb_rating", "score")
        popularity_series = pick_col("popularity", "vote_count")
        poster_series = pick_col("poster_url", "poster_path", "image_url")

        if title_series is None or overview_series is None:
            raise ValueError(
                f"Dataset is missing required 'title' or 'overview' columns. Found: {list(df.columns)}"
            )

        clean_df = pd.DataFrame()
        clean_df["title"] = title_series.astype(str).str.strip()
        clean_df["overview"] = overview_series.fillna("").astype(str).str.strip()

        if genre_series is not None:
            clean_df["genres"] = genre_series.apply(self._parse_genre_field)
        else:
            clean_df["genres"] = "Unknown"

        if release_series is not None:
            clean_df["release_date"] = release_series.fillna("").astype(str).str.strip()
        else:
            clean_df["release_date"] = ""

        clean_df["release_year"] = clean_df["release_date"].apply(self._extract_year)

        if vote_series is not None:
            clean_df["vote_average"] = pd.to_numeric(vote_series, errors="coerce").fillna(0.0).round(1)
        else:
            clean_df["vote_average"] = 0.0

        if popularity_series is not None:
            clean_df["popularity"] = pd.to_numeric(popularity_series, errors="coerce").fillna(0.0).round(2)
        else:
            clean_df["popularity"] = 0.0

        if poster_series is not None:
            def _normalize_poster(val: Any) -> str:
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    return ""
                s = str(val).strip()
                if s.startswith("/"):
                    return f"https://image.tmdb.org/t/p/w500{s}"
                return s if s.startswith("http") else ""

            clean_df["poster_url"] = poster_series.apply(_normalize_poster)
        else:
            clean_df["poster_url"] = ""

        # Filter out invalid rows and deduplicate
        clean_df = clean_df[
            (clean_df["title"].str.len() > 0)
            & (clean_df["title"].str.lower() != "nan")
            & (clean_df["overview"].str.len() >= 15)
            & (clean_df["overview"].str.lower() != "nan")
        ]
        clean_df = clean_df.drop_duplicates(subset=["title", "overview"], keep="first")

        # Sort by popularity & rating so the top N rows represent the best known films
        clean_df = clean_df.sort_values(
            by=["popularity", "vote_average"],
            ascending=[False, False],
        ).head(self.settings.max_dataset_rows)

        clean_df = clean_df.reset_index(drop=True)
        clean_df["id"] = clean_df.index + 1

        # Build rich semantic text for SentenceTransformers embedding
        year_text = clean_df["release_year"].apply(
            lambda y: f" ({int(y)})" if pd.notna(y) else ""
        )
        clean_df["search_text"] = (
            "Title: "
            + clean_df["title"]
            + year_text
            + " | Genres: "
            + clean_df["genres"]
            + " | Rating: "
            + clean_df["vote_average"].astype(str)
            + " | Overview: "
            + clean_df["overview"]
        )

        return clean_df

    def _download_from_huggingface(self) -> pd.DataFrame:
        """Download TMDB movie dataset from HuggingFace with fallback repositories."""
        from datasets import load_dataset

        candidate_datasets = [
            self.settings.hf_dataset_name,
            self.settings.hf_fallback_dataset_name,
            "AiresPucrs/tmdb-5000-movies",
        ]
        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_candidates = [
            ds for ds in candidate_datasets if ds and not (ds in seen or seen.add(ds))
        ]

        for repo_id in unique_candidates:
            try:
                logger.info("Attempting to download dataset from HuggingFace: %s", repo_id)
                dataset = load_dataset(repo_id, split="train")
                raw_df = dataset.to_pandas()
                clean_df = self._normalize_dataframe(raw_df)
                if not clean_df.empty:
                    logger.info(
                        "Successfully loaded and cleaned %d movies from '%s'",
                        len(clean_df),
                        repo_id,
                    )
                    return clean_df
            except Exception as exc:
                logger.warning("Could not load dataset '%s': %s", repo_id, exc)

        logger.warning("Using built-in curated fallback dataset (%d movies).", len(FALLBACK_MOVIES))
        return self._normalize_dataframe(pd.DataFrame(FALLBACK_MOVIES))

    def load_or_create_dataset(self, force_refresh: bool = False) -> pd.DataFrame:
        """Load cleaned movies CSV from disk or download and clean from HuggingFace."""
        csv_path: Path = self.settings.clean_csv_path
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        if csv_path.exists() and not force_refresh:
            try:
                logger.info("Loading existing clean movie dataset from %s", csv_path)
                df = pd.read_csv(csv_path)
                if not df.empty and "search_text" in df.columns:
                    return df
                logger.info("Existing CSV is incomplete; re-initializing dataset.")
            except Exception as exc:
                logger.warning("Failed to read existing CSV (%s), re-downloading.", exc)

        clean_df = self._download_from_huggingface()
        clean_df.to_csv(csv_path, index=False)
        logger.info("Saved %d clean movie records to %s", len(clean_df), csv_path)
        return clean_df
