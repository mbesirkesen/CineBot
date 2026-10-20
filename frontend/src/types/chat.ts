export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface FilterOptions {
  genre?: string | null;
  min_rating?: number | null;
  min_year?: number | null;
}

export interface MovieItem {
  id: number;
  title: string;
  overview: string;
  genres: string[];
  release_year?: number | null;
  release_date?: string | null;
  vote_average: number;
  popularity: number;
  poster_url?: string | null;
  similarity_score: number;
}

export interface ChatRequest {
  message: string;
  top_k: number;
  history: ChatHistoryMessage[];
  filters?: FilterOptions | null;
  previous_recommendations?: MovieItem[];
}

export interface ChatResponse {
  reply: string;
  recommendations: MovieItem[];
  query_used: string;
  llm_provider: string;
  latency_ms: number;
  follow_up?: boolean;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  dataset_loaded: boolean;
  total_movies: number;
  embedding_model: string;
  llm_provider: string;
}

export interface UIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  recommendations?: MovieItem[];
  llmProvider?: string;
  latencyMs?: number;
}
