import React, { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Send } from "lucide-react";
import { QUICK_PROMPTS } from "../constants";
import type { UIMessage } from "../types/chat";
import { ChatMessageItem } from "./ChatMessageItem";
import { ThinkingState } from "./ThinkingState";

interface ChatPanelProps {
  messages: UIMessage[];
  freshReplyId: string | null;
  input: string;
  isLoading: boolean;
  error: string | null;
  onInputChange: (value: string) => void;
  onSend: (text?: string) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  freshReplyId,
  input,
  isLoading,
  error,
  onInputChange,
  onSend,
}) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, isLoading, error]);

  return (
    <section className="flex min-h-[70vh] min-w-0 flex-col rounded-3xl border border-black/5 bg-white/45 shadow-xl shadow-amber-900/5 backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.03] dark:shadow-none lg:h-full lg:min-h-0">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
        {messages.map((message) => (
          <ChatMessageItem
            key={message.id}
            message={message}
            typewriter={message.id === freshReplyId}
          />
        ))}
        {isLoading && <ThinkingState />}
        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-200">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-black/5 p-3 dark:border-white/10 sm:p-4">
        <div className="mb-2.5 flex gap-2 overflow-x-auto pb-1">
          {QUICK_PROMPTS.map((prompt, index) => (
            <motion.button
              key={prompt.label}
              type="button"
              disabled={isLoading}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
              onClick={() => onSend(prompt.query)}
              className="whitespace-nowrap rounded-full border border-black/5 bg-white/80 px-3 py-1.5 text-[11px] text-slate-600 transition-all duration-300 hover:-translate-y-0.5 hover:border-amber-400/70 hover:text-slate-900 disabled:opacity-40 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:text-white"
            >
              {prompt.label}
            </motion.button>
          ))}
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSend();
          }}
          className="flex items-center gap-2 rounded-2xl border border-black/5 bg-white/80 p-1.5 shadow-sm dark:border-white/10 dark:bg-black/20"
        >
          <input
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            disabled={isLoading}
            placeholder="Bir ruh hali, tür ya da benzeyen bir film yaz..."
            className="w-full bg-transparent px-3 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 disabled:opacity-50 dark:text-white"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-3.5 py-2 text-xs font-semibold text-slate-950 transition-all duration-300 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Gönder
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>
    </section>
  );
};
