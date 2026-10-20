import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Calendar, Play, Star, X } from "lucide-react";
import { matchPercent, openTrailer, ratingLabel, recommendationReason } from "../constants";
import { MarkdownWithSpoilers, SpoilerGate } from "./SpoilerMarkdown";
import type { MovieItem } from "../types/chat";

interface DetailPanelProps {
  movie: MovieItem | null;
  reply: string;
  onClose: () => void;
}

export const DetailPanel: React.FC<DetailPanelProps> = ({ movie, reply, onClose }) => {
  return (
    <AnimatePresence>
      {movie && (
        <motion.div
          className="fixed inset-0 z-40 flex justify-end bg-slate-950/40 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.aside
            initial={{ x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 28, opacity: 0 }}
            transition={{ duration: 0.3 }}
            onClick={(event) => event.stopPropagation()}
            className="h-full w-full max-w-md overflow-y-auto border-l border-black/5 bg-[#f7f3ec] p-5 shadow-2xl dark:border-white/10 dark:bg-[#101624]"
          >
            <DetailBody movie={movie} reply={reply} onClose={onClose} />
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const DetailBody: React.FC<{ movie: MovieItem; reply: string; onClose: () => void }> = ({
  movie,
  reply,
  onClose,
}) => {
  const [broken, setBroken] = useState(false);
  const percent = matchPercent(movie.similarity_score);
  const reason = recommendationReason(
    movie.title,
    reply,
    `${movie.title}, sorguna %${percent} semantik yakınlıkla eşleşti. ${movie.genres.slice(0, 3).join(", ") || "Sinema"} türünde ve TMDB puanı ${movie.vote_average.toFixed(1)}.`,
    movie.release_year,
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
          Etkileşimli ayrıntı
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Kapat"
          className="rounded-full border border-black/5 p-1.5 text-slate-500 transition-all duration-300 hover:text-slate-900 dark:border-white/10 dark:hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="overflow-hidden rounded-3xl border border-black/5 bg-white shadow-xl shadow-amber-900/5 dark:border-white/10 dark:bg-white/5 dark:shadow-none">
        <div className="aspect-[16/9] bg-slate-200 dark:bg-slate-800">
          {movie.poster_url && !broken ? (
            <img
              src={movie.poster_url}
              alt=""
              className="h-full w-full object-cover"
              onError={() => setBroken(true)}
            />
          ) : null}
        </div>
        <div className="space-y-3 p-4">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{movie.title}</h3>
            <span className="rounded-full bg-teal-400/15 px-2 py-1 text-[11px] font-semibold text-teal-700 shadow-glow-teal dark:text-teal-300">
              %{percent} MATCH
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            {movie.release_year && (
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {movie.release_year}
              </span>
            )}
            <span className="inline-flex items-center gap-1">
              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
              {ratingLabel(movie.vote_average)} TMDB
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {movie.genres.map((genre) => (
              <span
                key={genre}
                className="rounded-full border border-black/5 px-2 py-0.5 text-[11px] text-slate-600 dark:border-white/10 dark:text-slate-300"
              >
                {genre}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-black/5 bg-white/80 p-4 dark:border-white/10 dark:bg-white/[0.04]">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Neden öneriyoruz?</h4>
        <div className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300 [&_p]:mb-2 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_strong]:text-slate-900 dark:[&_strong]:text-white [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-4">
          <MarkdownWithSpoilers text={reason} />
        </div>
      </div>

      {movie.overview.trim() && (
        <div className="mt-4 rounded-2xl border border-black/5 bg-white/80 p-4 dark:border-white/10 dark:bg-white/[0.04]">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Özet</h4>
          <SpoilerGate text={movie.overview} />
        </div>
      )}

      <button
        type="button"
        onClick={() => openTrailer(movie.title, movie.release_year)}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-3 text-sm font-semibold text-slate-950 transition-all duration-300 hover:brightness-110"
      >
        <Play className="h-4 w-4 fill-current" />
        Fragmanı aç
      </button>
    </div>
  );
};
