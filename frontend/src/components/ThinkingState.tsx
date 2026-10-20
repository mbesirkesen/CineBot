import React from "react";

export const ThinkingState: React.FC = () => {
  return (
    <div className="flex w-fit items-center gap-3 rounded-2xl border border-black/5 bg-white/70 px-3.5 py-2.5 shadow-sm backdrop-blur-md dark:border-white/10 dark:bg-white/5">
      <span className="relative flex h-2.5 w-2.5">
        <span className="breathe absolute inline-flex h-full w-full rounded-full bg-teal-400 shadow-glow-teal" />
      </span>
      <div className="flex h-4 items-end gap-0.5" aria-hidden>
        {[0, 1, 2, 3, 4].map((bar) => (
          <span
            key={bar}
            className="wave-bar w-0.5 rounded-full bg-teal-400/90"
            style={{
              height: "100%",
              animationDelay: `${bar * 0.12}s`,
            }}
          />
        ))}
      </div>
      <span className="text-xs text-slate-600 dark:text-slate-300">AI eşleştiriyor...</span>
    </div>
  );
};
