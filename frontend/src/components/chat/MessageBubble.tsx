import { useState, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, ThinkingStep } from "../../types/ui";
import { TracePanel } from "./TracePanel";

const TOOL_LABELS: Record<string, string> = {
  search_fips_codes: "Searching for locations",
  search_feature_schema: "Finding relevant data",
  get_field_descriptions: "Getting field details",
  execute_sql: "Running query",
};

function StepRow({ step }: { step: ThinkingStep }) {
  // Active steps (not complete) auto-expand; completed steps start collapsed
  const [expanded, setExpanded] = useState(!step.isComplete);

  // Auto-collapse when streaming completes
  useEffect(() => {
    if (step.isComplete) {
      setExpanded(false);
    }
  }, [step.isComplete]);

  const label = step.toolName
    ? (TOOL_LABELS[step.toolName] ?? step.toolName)
    : "Thinking...";

  return (
    <div className="mb-1">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 w-full text-left px-2 py-1 rounded hover:bg-gray-100 transition-colors"
      >
        <span
          className={`text-blue-500 text-sm select-none ${
            !step.isComplete ? "animate-pulse" : ""
          }`}
        >
          ✦
        </span>
        <span className="text-xs font-medium text-gray-600 flex-1">{label}</span>
        <span className="text-gray-400 text-xs">{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && step.thinking && (
        <div className="pl-6 pr-2 py-1">
          <p className="text-xs italic text-gray-500 whitespace-pre-wrap leading-relaxed">
            {step.thinking}
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

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-white border border-gray-200 text-gray-900"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            {/* Thinking steps panel — shown above the final answer */}
            {message.steps && message.steps.length > 0 && (
              <div className="mb-3 border border-gray-100 rounded-md p-1">
                {message.steps.map((step, i) => (
                  <StepRow key={i} step={step} />
                ))}
              </div>
            )}

            {/* Final answer */}
            <div className="prose prose-sm max-w-none">
              <Markdown remarkPlugins={[remarkGfm]}>
                {message.content ||
                  (message.steps && message.steps.length > 0 ? "" : "Thinking...")}
              </Markdown>
            </div>

            {/* Trace panel — shown below the answer when trace data is available */}
            {message.trace && <TracePanel trace={message.trace} />}
          </>
        )}
      </div>
    </div>
  );
}
