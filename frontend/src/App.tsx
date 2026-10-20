import React, { useEffect, useMemo, useState } from "react";
import { ChatPanel } from "./components/ChatPanel";
import { DetailPanel } from "./components/DetailPanel";
import { SpotlightPanel } from "./components/SpotlightPanel";
import { TopBar } from "./components/TopBar";
import { useTheme } from "./hooks/useTheme";
import { fetchHealthStatus, sendChatMessage } from "./services/api";
import type {
  ChatHistoryMessage,
  FilterOptions,
  HealthResponse,
  MovieItem,
  UIMessage,
} from "./types/chat";

const CHAT_STORAGE_KEY = "cinebot-chat";
/** Backend rejects history turns longer than 8000 chars; stay well under it. */
const HISTORY_CHAR_LIMIT = 3500;

const INITIAL_WELCOME_MESSAGE: UIMessage = {
  id: "welcome-msg",
  role: "assistant",
  content:
    "Merhaba, ben CineBot.\n\n" +
    "Ruh halini, sevdiğin bir temayı ya da benzeyen bir filmi yaz. FAISS vektör uzayında en yakın filmleri bulup neden uyduklarını anlatacağım.",
  timestamp: new Date().toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
  }),
};

function loadStoredMessages(): UIMessage[] {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return [INITIAL_WELCOME_MESSAGE];
    const parsed = JSON.parse(raw) as UIMessage[];
    if (!Array.isArray(parsed) || parsed.length === 0) return [INITIAL_WELCOME_MESSAGE];
    return parsed.slice(-40);
  } catch {
    return [INITIAL_WELCOME_MESSAGE];
  }
}

export const App: React.FC = () => {
  const { theme, toggle } = useTheme();
  const [messages, setMessages] = useState<UIMessage[]>(loadStoredMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [topK, setTopK] = useState(3);
  const [filters, setFilters] = useState<FilterOptions>({
    genre: null,
    min_rating: null,
    min_year: null,
  });
  const [freshReplyId, setFreshReplyId] = useState<string | null>(null);
  const [detailMovie, setDetailMovie] = useState<MovieItem | null>(null);
  const [detailReply, setDetailReply] = useState("");

  useEffect(() => {
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages.slice(-40)));
    } catch {
      // A full browser quota should not block the chat itself.
    }
  }, [messages]);

  useEffect(() => {
    let mounted = true;
    fetchHealthStatus()
      .then((response) => {
        if (mounted) setHealth(response);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, []);

  const latestAssistant = useMemo(
    () => [...messages].reverse().find((message) => message.recommendations && message.recommendations.length > 0),
    [messages],
  );
  const spotlightMovies = latestAssistant?.recommendations ?? [];

  const handleSendMessage = async (rawText?: string) => {
    const query = (rawText ?? input).trim();
    if (!query || isLoading) return;

    setError(null);
    setDetailMovie(null);
    if (!rawText) setInput("");

    const userMsg: UIMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
    };
    const historyPayload: ChatHistoryMessage[] = messages
      .filter((message) => message.id !== "welcome-msg")
      .slice(-6)
      .map((message) => ({
        role: message.role,
        content: message.content.replace(/\|\|/g, "").slice(0, HISTORY_CHAR_LIMIT),
      }))
      .filter((message) => message.content.trim().length > 0);

    setMessages((previous) => [...previous, userMsg]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage({
        message: query,
        top_k: topK,
        history: historyPayload,
        filters,
        previous_recommendations: (latestAssistant?.recommendations ?? []).slice(0, 15),
      });
      const botMsg: UIMessage = {
        id: `bot-${Date.now()}`,
        role: "assistant",
        content: response.reply,
        timestamp: new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
        recommendations: response.recommendations,
        llmProvider: response.llm_provider,
        latencyMs: response.latency_ms,
      };
      setFreshReplyId(botMsg.id);
      setMessages((previous) => [...previous, botMsg]);
      if (!health) {
        fetchHealthStatus().then(setHealth).catch(() => undefined);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sunucu ile iletişim kurulamadı.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        ...INITIAL_WELCOME_MESSAGE,
        timestamp: new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setError(null);
    setFreshReplyId(null);
    setDetailMovie(null);
    localStorage.removeItem(CHAT_STORAGE_KEY);
  };

  return (
    <div className="relative flex min-h-screen flex-col bg-cinema-ivory text-slate-900 transition-all duration-300 dark:bg-[#070b14] dark:text-slate-100 lg:h-screen lg:overflow-hidden">
      <div className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full bg-amber-300/30 blur-3xl dark:bg-amber-500/10" />
      <div className="pointer-events-none absolute right-0 top-1/3 h-80 w-80 rounded-full bg-sky-300/25 blur-3xl dark:bg-teal-400/10" />
      <div className="film-grain" />

      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        <TopBar
          health={health}
          filters={filters}
          topK={topK}
          theme={theme}
          onToggleTheme={toggle}
          onChangeFilters={setFilters}
          onChangeTopK={setTopK}
          onClearChat={handleClearChat}
        />

        <main className="grid min-h-0 flex-1 gap-4 p-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:overflow-hidden">
          <ChatPanel
            messages={messages}
            freshReplyId={freshReplyId}
            input={input}
            isLoading={isLoading}
            error={error}
            onInputChange={setInput}
            onSend={(text) => void handleSendMessage(text)}
          />

          <aside className="flex min-h-[32rem] min-w-0 flex-col gap-4 lg:h-full lg:min-h-0">
            <div className="min-h-0 flex-1 overflow-y-auto">
              <SpotlightPanel
                movies={spotlightMovies}
                selectedId={detailMovie?.id ?? spotlightMovies[0]?.id ?? null}
                onSelect={(movie) => {
                  setDetailMovie(movie);
                  setDetailReply(latestAssistant?.content ?? "");
                }}
                isLoading={isLoading}
              />
            </div>
          </aside>
        </main>
      </div>

      <DetailPanel movie={detailMovie} reply={detailReply} onClose={() => setDetailMovie(null)} />
    </div>
  );
};

export default App;
