export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  username: string;
}

export interface CreateSessionRequest {
  title?: string;
}

export interface SessionInfo {
  session_id: string;
  title: string;
  created_at: string;
}

export interface MessageRequest {
  content: string;
}

export interface MessageResponse {
  role: string;
  content: string;
  timestamp: string;
  trace?: string;
}

export interface SSEEvent {
  event: "step_start" | "thinking_delta" | "tool_use" | "tool_result" | "done" | "trace" | "error";
  data: string;
}
