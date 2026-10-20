import React, { useState } from "react";
import { motion } from "framer-motion";
import { Film } from "lucide-react";
import { matchPercent, ratingLabel } from "../constants";
import type { MovieItem } from "../types/chat";

interface SpotlightPanelProps {
  movies: MovieItem[];
  selectedId: number | null;
  onSelect: (movie: MovieItem) => void;
  isLoading?: boolean;
}

export const SpotlightPanel: React.FC<SpotlightPanelProps> = ({ movies, selectedId, onSelect, isLoading = false }) => {
  return (
    <section className="flex min-h-0 flex-col gap-3">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          Spotlight
        </h2>
        <span className="text-[11px] text-slate-400">
          {isLoading ? "Aranıyor…" : movies.length ? `${movies.length} eşleşme` : "Bekleniyor"}
        </span>
      </div>

      {movies.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-3xl border border-dashed border-black/10 bg-white/40 px-6 py-10 text-center text-sm text-slate-500 dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-400">
          Bir arama yaz. Semantik olarak en yakın filmler burada kart olarak belirecek.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          {movies.map((movie, index) => (
            <SpotlightCard
              key={movie.id}
              movie={movie}
              index={index}
              active={movie.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </section>
  );
};

const SpotlightCard: React.FC<{
  movie: MovieItem;
  index: number;
  active: boolean;
  onSelect: (movie: MovieItem) => void;
}> = ({ movie, index, active, onSelect }) => {
  const [broken, setBroken] = useState(false);
  const percent = matchPercent(movie.similarity_score);

  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.06 }}
      onClick={() => onSelect(movie)}
      className={`group flex gap-3 rounded-2xl border p-2.5 text-left transition-all duration-300 hover:-translate-y-0.5 ${
        active
          ? "border-amber-400/70 bg-white/80 shadow-glow dark:bg-white/10"
          : "border-black/5 bg-white/70 shadow-xl shadow-amber-900/5 hover:border-amber-300/50 dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none"
      }`}
    >
      <div className="h-24 w-16 flex-shrink-0 overflow-hidden rounded-xl bg-slate-200 dark:bg-slate-800">
        {movie.poster_url && !broken ? (
          <img
            src={movie.poster_url}
            alt=""
            className="h-full w-full object-cover transition-all duration-300 group-hover:scale-105"
            onError={() => setBroken(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-amber-500">
            <Film className="h-5 w-5" />
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="truncate text-sm font-semibold text-slate-900 dark:text-white">{movie.title}</h3>
          <span
            className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${
              percent >= 60
                ? "bg-teal-400/15 text-teal-700 shadow-glow-teal dark:text-teal-300"
                : "bg-amber-400/15 text-amber-700 dark:text-amber-300"
            }`}
          >
            %{percent} MATCH
          </span>
        </div>
        <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
          {movie.release_year ?? "—"} · ⭐ {ratingLabel(movie.vote_average)}
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          {movie.genres.slice(0, 2).map((genre) => (
            <span
              key={genre}
              className="rounded-full border border-black/5 px-1.5 py-0.5 text-[10px] text-slate-500 dark:border-white/10 dark:text-slate-300"
            >
              {genre}
            </span>
          ))}
        </div>
      </div>
    </motion.button>
  );
};
