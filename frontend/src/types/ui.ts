export interface ThinkingStep {
  thinking: string;        // live reasoning text (streams in char by char)
  toolName?: string;       // set when tool_use event fires
  toolInput?: unknown;
  toolResult?: string;     // set when tool_result event fires
  isComplete: boolean;     // true once tool_result received or end_turn reached
}

export interface TraceIteration {
  iteration: number;
  thinking?: string;
  tool?: string;
  tool_input?: Record<string, unknown>;
  tool_result?: string;
}

export interface TraceData {
  session_id: string;
  message_id: string;
  user_message: string;
  timestamp: string;
  iterations: TraceIteration[];
  final_response: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  steps?: ThinkingStep[];
  trace?: TraceData;
}
