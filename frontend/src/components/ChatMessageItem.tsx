import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bot, Clock, Sparkles, User } from "lucide-react";
import type { UIMessage } from "../types/chat";
import { MarkdownWithSpoilers } from "./SpoilerMarkdown";

interface ChatMessageItemProps {
  message: UIMessage;
  typewriter?: boolean;
}

const markdownComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-2.5 last:mb-0">{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="italic text-amber-700 dark:text-amber-200">{children}</em>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="mb-2.5 list-disc space-y-2 pl-4 last:mb-0">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="mb-2.5 list-decimal space-y-2 pl-4 last:mb-0">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="leading-relaxed [&>p]:mb-1 [&>p:last-child]:mb-0">{children}</li>
  ),
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="mb-2 text-base font-semibold text-slate-900 dark:text-white">{children}</h3>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="mb-2 text-base font-semibold text-slate-900 dark:text-white">{children}</h3>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">{children}</h3>
  ),
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-amber-600 underline dark:text-amber-300">
      {children}
    </a>
  ),
};

function useTypewriter(text: string, enabled: boolean): string {
  const [count, setCount] = useState(enabled ? 0 : text.length);

  useEffect(() => {
    if (!enabled) {
      setCount(text.length);
      return;
    }
    setCount(0);
    const timer = window.setInterval(() => {
      setCount((current) => {
        if (current >= text.length) {
          window.clearInterval(timer);
          return current;
        }
        return Math.min(text.length, current + 3);
      });
    }, 16);
    return () => window.clearInterval(timer);
  }, [enabled, text]);

  return text.slice(0, count);
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message, typewriter = false }) => {
  const isUser = message.role === "user";
  const shown = useTypewriter(message.content, typewriter && !isUser);

  useEffect(() => {
    if (!typewriter) return;
    document.getElementById(`msg-${message.id}`)?.scrollIntoView({ block: "end" });
  }, [shown, typewriter, message.id]);

  return (
    <motion.div
      id={`msg-${message.id}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 text-white dark:from-slate-200 dark:to-slate-400 dark:text-slate-950">
          <Bot className="h-4 w-4" />
        </div>
      )}

      <div className={`max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed transition-all duration-300 ${
            isUser
              ? "rounded-tr-md bg-gradient-to-r from-amber-400 to-amber-500 font-medium text-slate-950 shadow-glow"
              : "rounded-tl-md border border-black/5 bg-white/75 text-slate-800 shadow-xl shadow-amber-900/5 backdrop-blur-md dark:border-white/10 dark:bg-white/[0.06] dark:text-slate-200 dark:shadow-none"
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-line">{message.content}</div>
          ) : (
            <MarkdownWithSpoilers text={shown} components={markdownComponents} />
          )}
          <div
            className={`mt-2 flex flex-wrap items-center gap-2 text-[10px] ${
              isUser ? "text-slate-900/70" : "text-slate-400"
            }`}
          >
            <span>{message.timestamp}</span>
            {!isUser && message.llmProvider && (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-900/5 px-1.5 py-0.5 font-medium text-amber-700 dark:bg-white/10 dark:text-amber-300">
                <Sparkles className="h-2.5 w-2.5" />
                {message.llmProvider.toUpperCase()}
              </span>
            )}
            {!isUser && typeof message.latencyMs === "number" && (
              <span className="inline-flex items-center gap-1">
                <Clock className="h-2.5 w-2.5" />
                {Math.round(message.latencyMs)} ms
              </span>
            )}
          </div>
        </div>
      </div>

      {isUser && (
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl border border-amber-300/40 bg-amber-100 text-amber-800 dark:border-white/10 dark:bg-white/10 dark:text-amber-200">
          <User className="h-4 w-4" />
        </div>
      )}
    </motion.div>
  );
};
