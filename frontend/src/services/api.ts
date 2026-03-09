import { API_BASE_URL } from "../config";
import type {
  LoginRequest,
  LoginResponse,
  SessionInfo,
  MessageResponse,
  SSEEvent,
} from "../types/api";

function getToken(): string | null {
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth
export async function login(data: LoginRequest): Promise<LoginResponse> {
  return request<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getMe(): Promise<{ username: string }> {
  return request("/api/auth/me");
}

// Sessions
export async function createSession(
  title?: string
): Promise<SessionInfo> {
  return request<SessionInfo>("/api/chat/sessions", {
    method: "POST",
    body: JSON.stringify({ title: title || "New Chat" }),
  });
}

export async function listSessions(): Promise<SessionInfo[]> {
  return request<SessionInfo[]>("/api/chat/sessions");
}

export async function getSessionMessages(
  sessionId: string
): Promise<MessageResponse[]> {
  return request<MessageResponse[]>(`/api/chat/sessions/${sessionId}`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  return request<void>(`/api/chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

// SSE streaming message
export async function sendMessage(
  sessionId: string,
  content: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const token = getToken();
  const res = await fetch(
    `${API_BASE_URL}/api/chat/sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
      signal,
    }
  );

  if (!res.ok) {
    throw new Error(await res.text());
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ") && currentEvent) {
        const data = line.slice(6);
        onEvent({
          event: currentEvent as SSEEvent["event"],
          data,
        });
        currentEvent = "";
      }
    }
  }
}
