import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";

type SpoilerPart =
  | { kind: "text"; text: string }
  | { kind: "spoiler"; text: string; ready: boolean };

export function splitSpoilers(source: string): SpoilerPart[] {
  const text = source.endsWith("|") && !source.endsWith("||") ? source.slice(0, -1) : source;
  const parts: SpoilerPart[] = [];
  const pattern = /\|\|([\s\S]*?)\|\|/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text))) {
    if (match.index > last) {
      parts.push({ kind: "text", text: text.slice(last, match.index) });
    }
    parts.push({ kind: "spoiler", text: match[1].trim(), ready: true });
    last = match.index + match[0].length;
  }

  const rest = text.slice(last);
  const open = rest.indexOf("||");
  if (open >= 0) {
    if (open > 0) parts.push({ kind: "text", text: rest.slice(0, open) });
    parts.push({ kind: "spoiler", text: "", ready: false });
  } else if (rest) {
    parts.push({ kind: "text", text: rest });
  }

  return parts;
}

export const SpoilerGate: React.FC<{
  text: string;
  ready?: boolean;
  components?: Components;
}> = ({ text, ready = true, components }) => {
  const [open, setOpen] = useState(false);

  if (!ready || !open) {
    return (
      <button
        type="button"
        disabled={!ready}
        onClick={() => setOpen(true)}
        className="my-2 flex w-full items-center gap-3 rounded-xl border border-dashed border-amber-400/50 bg-amber-400/10 px-3 py-2.5 text-left text-amber-800 transition-all duration-300 hover:bg-amber-400/20 disabled:cursor-default disabled:opacity-70 dark:text-amber-200"
      >
        <EyeOff className="h-4 w-4 flex-shrink-0" />
        <span>
          <span className="block text-xs font-semibold">Spoiler uyarısı</span>
          <span className="block text-[11px] text-amber-700/80 dark:text-amber-100/70">
            {ready ? "Konu gizli. Görmek için tıkla." : "Gizleniyor…"}
          </span>
        </span>
      </button>
    );
  }

  return (
    <div className="my-2 rounded-xl border border-amber-400/40 bg-amber-400/10 px-3 py-2.5 text-slate-700 dark:text-slate-200">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-amber-700 dark:text-amber-200">
          Spoiler
        </span>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-800 hover:underline dark:text-amber-100"
        >
          <Eye className="h-3 w-3" />
          Gizle
        </button>
      </div>
      {components ? (
        <ReactMarkdown components={components}>{text}</ReactMarkdown>
      ) : (
        <p className="whitespace-pre-line leading-relaxed">{text}</p>
      )}
    </div>
  );
};

export const MarkdownWithSpoilers: React.FC<{
  text: string;
  components?: Components;
}> = ({ text, components }) => {
  const parts = splitSpoilers(text);

  return (
    <>
      {parts.map((part, index) => {
        if (part.kind === "spoiler") {
          return <SpoilerGate key={`spoiler-${index}`} text={part.text} ready={part.ready} components={components} />;
        }
        if (!part.text.trim()) return null;
        return (
          <ReactMarkdown key={`text-${index}`} components={components}>
            {part.text}
          </ReactMarkdown>
        );
      })}
    </>
  );
};
