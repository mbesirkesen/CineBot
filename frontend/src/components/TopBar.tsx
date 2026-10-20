import React from "react";
import { motion } from "framer-motion";
import { Clapperboard, Cpu, Database, Moon, Sparkles, Sun, Trash2 } from "lucide-react";
import { GENRE_OPTIONS } from "../constants";
import type { ThemeMode } from "../hooks/useTheme";
import type { FilterOptions, HealthResponse } from "../types/chat";

interface TopBarProps {
  health: HealthResponse | null;
  filters: FilterOptions;
  topK: number;
  theme: ThemeMode;
  onToggleTheme: () => void;
  onChangeFilters: (next: FilterOptions) => void;
  onChangeTopK: (topK: number) => void;
  onClearChat: () => void;
}

const selectClass =
  "rounded-full border border-black/5 bg-white/70 px-3 py-1.5 text-xs text-slate-700 shadow-sm outline-none transition-all duration-300 hover:border-amber-400/70 focus:border-amber-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-amber-300/50";

export const TopBar: React.FC<TopBarProps> = ({
  health,
  filters,
  topK,
  theme,
  onToggleTheme,
  onChangeFilters,
  onChangeTopK,
  onClearChat,
}) => {
  return (
    <header className="relative z-20 border-b border-black/5 bg-white/55 backdrop-blur-xl dark:border-white/10 dark:bg-[#0b1020]/70">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-rose-500 shadow-glow">
            <Clapperboard className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-tight text-slate-900 dark:text-white">
                CineBot
              </h1>
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-700 dark:text-amber-300">
                NLP
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Semantik film eşleştirme
            </p>
          </div>
        </div>

        <div className="flex flex-1 flex-wrap items-center gap-2 sm:justify-center">
          <StatPill icon={<Database className="h-3.5 w-3.5 text-emerald-500" />}>
            {health ? `${health.total_movies.toLocaleString("tr-TR")} Film` : "Bağlanıyor"}
          </StatPill>
          <StatPill icon={<Cpu className="h-3.5 w-3.5 text-sky-500" />}>
            {health?.embedding_model ?? "paraphrase-multilingual-MiniLM-L12-v2"}
          </StatPill>
          <StatPill icon={<Sparkles className="h-3.5 w-3.5 text-amber-500" />}>
            {health ? health.llm_provider.toUpperCase() : "LLM"}
          </StatPill>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-black/5 bg-white/80 text-amber-600 transition-all duration-300 hover:scale-105 dark:border-white/10 dark:bg-white/5 dark:text-amber-300"
          >
            <motion.span
              key={theme}
              initial={{ rotate: -40, scale: 0.6, opacity: 0 }}
              animate={{ rotate: 0, scale: 1, opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="flex"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </motion.span>
          </button>
          <button
            type="button"
            onClick={onClearChat}
            aria-label="Sohbeti temizle"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-black/5 bg-white/80 text-slate-500 transition-all duration-300 hover:text-rose-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-black/5 px-4 py-2.5 dark:border-white/10 sm:px-5">
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
          Arayüz filtreleri
        </span>
        <select
          value={filters.genre || ""}
          onChange={(event) =>
            onChangeFilters({ ...filters, genre: event.target.value || null })
          }
          className={selectClass}
          aria-label="Tür"
        >
          {GENRE_OPTIONS.map((genre) => (
            <option key={genre.value || "all"} value={genre.value}>
              {genre.label}
            </option>
          ))}
        </select>
        <select
          value={filters.min_rating ?? ""}
          onChange={(event) =>
            onChangeFilters({
              ...filters,
              min_rating: event.target.value ? Number(event.target.value) : null,
            })
          }
          className={selectClass}
          aria-label="Minimum puan"
        >
          <option value="">Min puan</option>
          <option value="6">6.0+</option>
          <option value="7">7.0+</option>
          <option value="7.5">7.5+</option>
          <option value="8">8.0+</option>
        </select>
        <select
          value={filters.min_year ?? ""}
          onChange={(event) =>
            onChangeFilters({
              ...filters,
              min_year: event.target.value ? Number(event.target.value) : null,
            })
          }
          className={selectClass}
          aria-label="Minimum yıl"
        >
          <option value="">Min yıl</option>
          <option value="1990">1990+</option>
          <option value="2000">2000+</option>
          <option value="2010">2010+</option>
          <option value="2018">2018+</option>
        </select>
        <select
          value={topK}
          onChange={(event) => onChangeTopK(Number(event.target.value))}
          className={`${selectClass} sm:ml-auto`}
          aria-label="Öneri sayısı"
        >
          <option value={3}>3 film</option>
          <option value={5}>5 film</option>
          <option value={8}>8 film</option>
        </select>
      </div>
    </header>
  );
};

const StatPill: React.FC<{ icon: React.ReactNode; children: React.ReactNode }> = ({
  icon,
  children,
}) => (
  <span className="inline-flex items-center gap-1.5 rounded-full border border-black/5 bg-white/70 px-2.5 py-1 text-[11px] font-medium text-slate-600 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
    {icon}
    {children}
  </span>
);
