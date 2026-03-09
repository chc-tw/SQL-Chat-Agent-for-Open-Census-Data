import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import type { ChatMessage } from "../../types/ui";

const SUGGESTION_CHIPS = [
  "Population of Fulton County, GA in 2019",
  "Median household income by state",
  "Age distribution in New York City 2020",
  "Educational attainment in Texas 2019",
];

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSend: (content: string) => void;
}

export function ChatWindow({ messages, isStreaming, onSend }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-[var(--bg-base)]">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-6 py-12">
            {/* Hero mark */}
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center mb-6"
              style={{
                background: "linear-gradient(135deg, var(--accent), var(--cyan))",
                boxShadow: "0 0 40px var(--accent-dim)",
              }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="4" fill="white" />
                <path
                  d="M12 4v3M12 17v3M4 12h3M17 12h3"
                  stroke="white"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </div>

            <h2
              className="text-2xl font-bold text-[var(--text-hi)] mb-2 text-center"
              style={{ fontFamily: "Syne, sans-serif" }}
            >
              Census AI
            </h2>
            <p className="text-sm text-[var(--text-mid)] text-center mb-10 max-w-xs leading-relaxed">
              Ask natural language questions about US Census data from 2019–2020.
              Powered by Snowflake + Claude.
            </p>

            {/* Suggestion chips */}
            <div className="w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-2">
              {SUGGESTION_CHIPS.map((chip) => (
                <button
                  key={chip}
                  onClick={() => onSend(chip)}
                  className="text-left px-4 py-3 rounded-xl border border-[var(--border-mid)] text-sm text-[var(--text-mid)] hover:border-[var(--accent)] hover:text-[var(--text-hi)] hover:bg-[var(--accent-dim)] transition-all duration-150"
                  style={{ background: "var(--bg-surface)" }}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="px-4 py-6 space-y-0 max-w-4xl mx-auto w-full">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}

            {/* Typing indicator */}
            {isStreaming && messages[messages.length - 1]?.content === "" && (
              <div className="flex justify-start mb-4">
                <div
                  className="rounded-2xl rounded-tl-sm border border-[var(--border-dim)] px-4 py-3 flex items-center gap-2"
                  style={{ background: "var(--bg-card)" }}
                >
                  <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                  <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                  <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <MessageInput onSend={onSend} disabled={isStreaming} />
    </div>
  );
}
