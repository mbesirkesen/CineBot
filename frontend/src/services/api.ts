import type { ChatRequest, ChatResponse, HealthResponse } from "../types/chat";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchHealthStatus(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Sunucu durum kontrolü başarısız oldu: ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errJson = (await response.json()) as { detail?: string };
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<ChatResponse>;
}
