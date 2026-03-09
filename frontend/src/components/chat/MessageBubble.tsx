import { useState, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, ThinkingStep } from "../../types/ui";
import { TracePanel } from "./TracePanel";

const TOOL_LABELS: Record<string, string> = {
  search_fips_codes: "Searching for locations",
  search_feature_schema: "Finding relevant data",
  get_field_descriptions: "Getting field details",
  execute_sql: "Running SQL query",
};

const TOOL_ICONS: Record<string, string> = {
  search_fips_codes: "◎",
  search_feature_schema: "⊹",
  get_field_descriptions: "≡",
  execute_sql: "▷",
};

function StepRow({ step }: { step: ThinkingStep }) {
  const [expanded, setExpanded] = useState(!step.isComplete);

  useEffect(() => {
    if (step.isComplete) {
      setExpanded(false);
    }
  }, [step.isComplete]);

  const label = step.toolName
    ? (TOOL_LABELS[step.toolName] ?? step.toolName)
    : "Thinking…";
  const icon = step.toolName ? (TOOL_ICONS[step.toolName] ?? "✦") : "✦";

  return (
    <div className="mb-0.5">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2.5 w-full text-left px-2.5 py-1.5 rounded-lg transition-colors duration-150 hover:bg-[var(--bg-elevated)]"
      >
        <span
          className={`text-xs select-none flex-shrink-0 ${!step.isComplete ? "sparkle-active" : ""}`}
          style={{ color: step.isComplete ? "var(--accent)" : "var(--cyan)" }}
        >
          {icon}
        </span>
        <span className="text-xs text-[var(--text-mid)] flex-1 text-left">{label}</span>
        {step.isComplete && (
          <span className="text-[var(--text-lo)] text-xs">
            {expanded ? "▲" : "▼"}
          </span>
        )}
        {!step.isComplete && (
          <span className="flex gap-0.5">
            <span className="thinking-dot w-1 h-1 rounded-full inline-block bg-[var(--text-lo)]" />
            <span className="thinking-dot w-1 h-1 rounded-full inline-block bg-[var(--text-lo)]" />
            <span className="thinking-dot w-1 h-1 rounded-full inline-block bg-[var(--text-lo)]" />
          </span>
        )}
      </button>
      {expanded && (step.thinking || step.toolName) && (
        <div className="px-3 py-2 mx-2 rounded-lg border border-[var(--border-dim)] mb-1" style={{ background: "var(--bg-base)" }}>
          <p
            className="text-xs italic whitespace-pre-wrap leading-relaxed"
            style={{ color: "var(--text-mid)", fontFamily: "JetBrains Mono, monospace" }}
          >
            {step.thinking || `Using tool ${step.toolName}`}
          </p>
        </div>
      )}
    </div>
  );
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 msg-enter">
        <div
          className="max-w-[75%] rounded-2xl rounded-tr-sm px-4 py-3 text-white text-sm leading-relaxed"
          style={{
            background: "linear-gradient(135deg, var(--accent) 0%, var(--cyan) 100%)",
            boxShadow: "0 4px 20px var(--accent-dim)",
          }}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-4 msg-enter">
      <div
        className="max-w-[82%] rounded-2xl rounded-tl-sm border border-[var(--border-dim)] px-4 py-3"
        style={{ background: "var(--bg-card)" }}
      >
        {/* Thinking steps */}
        {message.steps && message.steps.length > 0 && (
          <div
            className="mb-3 rounded-lg border border-[var(--border-dim)] py-1 px-1"
            style={{ background: "var(--bg-elevated)" }}
          >
            {message.steps.map((step, i) => (
              <StepRow key={i} step={step} />
            ))}
          </div>
        )}

        {/* Final answer */}
        <div
          className="prose prose-sm max-w-none
            prose-headings:text-[var(--text-hi)] prose-headings:font-semibold
            prose-p:text-[var(--text-hi)] prose-p:leading-relaxed
            prose-strong:text-[var(--text-hi)] prose-strong:font-semibold
            prose-code:text-[var(--cyan)] prose-code:bg-[var(--bg-elevated)] prose-code:rounded prose-code:px-1 prose-code:py-0.5 prose-code:text-xs
            prose-pre:bg-[var(--bg-base)] prose-pre:border prose-pre:border-[var(--border-dim)] prose-pre:rounded-xl
            prose-a:text-[var(--accent)] prose-a:no-underline hover:prose-a:underline
            prose-ul:text-[var(--text-hi)] prose-ol:text-[var(--text-hi)]
            prose-li:text-[var(--text-hi)]
            prose-blockquote:border-l-[var(--accent)] prose-blockquote:text-[var(--text-mid)]
          "
        >
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ children }) => (
                <div className="overflow-x-auto my-3 rounded-xl border border-[var(--border-mid)]">
                  <table className="min-w-full border-collapse text-sm">{children}</table>
                </div>
              ),
              thead: ({ children }) => (
                <thead style={{ background: "var(--bg-elevated)" }}>{children}</thead>
              ),
              th: ({ children }) => (
                <th
                  className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider border-b border-[var(--border-mid)]"
                  style={{ color: "var(--text-lo)" }}
                >
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td
                  className="px-3 py-2 text-sm border-b border-[var(--border-dim)]"
                  style={{ color: "var(--text-hi)" }}
                >
                  {children}
                </td>
              ),
              tr: ({ children }) => (
                <tr className="hover:bg-[var(--bg-elevated)]/50 transition-colors">{children}</tr>
              ),
              code: ({ children, className }) => {
                const isBlock = className?.includes("language-");
                if (isBlock) {
                  return (
                    <code
                      className={className}
                      style={{ fontFamily: "JetBrains Mono, monospace" }}
                    >
                      {children}
                    </code>
                  );
                }
                return (
                  <code
                    className="rounded px-1 py-0.5 text-xs"
                    style={{
                      background: "var(--bg-elevated)",
                      color: "var(--cyan)",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content ||
              (message.steps && message.steps.length > 0 ? "" : "Thinking…")}
          </Markdown>
        </div>

        {/* Usage stats */}
        {message.trace && (message.trace.input_tokens != null || message.trace.duration_ms != null) && (
          <div className="mt-3 pt-3 border-t border-[var(--border-dim)] flex items-center gap-4 flex-wrap">
            {message.trace.input_tokens != null && (
              <span className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-lo)" }}>
                <span style={{ color: "var(--accent)", fontFamily: "JetBrains Mono, monospace" }}>↑</span>
                <span style={{ fontFamily: "JetBrains Mono, monospace" }}>{message.trace.input_tokens.toLocaleString()}</span>
                <span>in</span>
              </span>
            )}
            {message.trace.output_tokens != null && (
              <span className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-lo)" }}>
                <span style={{ color: "var(--cyan)", fontFamily: "JetBrains Mono, monospace" }}>↓</span>
                <span style={{ fontFamily: "JetBrains Mono, monospace" }}>{message.trace.output_tokens.toLocaleString()}</span>
                <span>out</span>
              </span>
            )}
            {message.trace.duration_ms != null && (
              <span className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-lo)" }}>
                <span style={{ color: "var(--text-lo)" }}>⏱</span>
                <span style={{ fontFamily: "JetBrains Mono, monospace" }}>
                  {message.trace.duration_ms >= 1000
                    ? `${(message.trace.duration_ms / 1000).toFixed(1)}s`
                    : `${message.trace.duration_ms}ms`}
                </span>
              </span>
            )}
          </div>
        )}

        {/* Trace panel */}
        {message.trace && <TracePanel trace={message.trace} />}
      </div>
    </div>
  );
}
