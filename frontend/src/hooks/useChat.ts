import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, ThinkingStep, TraceData } from "../types/ui";
import type { SSEEvent } from "../types/api";
import { getSessionMessages, sendMessage } from "../services/api";

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    getSessionMessages(sessionId).then((msgs) => {
      setMessages(
        msgs.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
          trace: m.trace ? (JSON.parse(m.trace) as TraceData) : undefined,
        }))
      );
    });
  }, [sessionId]);

  const send = useCallback(
    async (content: string) => {
      if (!sessionId || isStreaming) return;

      setMessages((prev) => [...prev, { role: "user", content }]);
      setIsStreaming(true);

      // Placeholder assistant message
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", steps: [] },
      ]);

      const currentSteps: ThinkingStep[] = [];

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await sendMessage(
          sessionId,
          content,
          (event: SSEEvent) => {
            switch (event.event) {
              case "step_start": {
                currentSteps.push({ thinking: "", isComplete: false });
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last) {
                    updated[updated.length - 1] = {
                      ...last,
                      steps: [...currentSteps],
                    };
                  }
                  return updated;
                });
                break;
              }
              case "thinking_delta": {
                if (currentSteps.length > 0) {
                  const lastStep = currentSteps[currentSteps.length - 1]!;
                  lastStep.thinking += event.data;
                }
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last) {
                    updated[updated.length - 1] = {
                      ...last,
                      steps: [...currentSteps],
                    };
                  }
                  return updated;
                });
                break;
              }
              case "tool_use": {
                const parsed = JSON.parse(event.data) as { name: string; input: unknown };
                if (currentSteps.length > 0) {
                  const lastStep = currentSteps[currentSteps.length - 1]!;
                  lastStep.toolName = parsed.name;
                  lastStep.toolInput = parsed.input;
                }
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last) {
                    updated[updated.length - 1] = {
                      ...last,
                      steps: [...currentSteps],
                    };
                  }
                  return updated;
                });
                break;
              }
              case "tool_result": {
                const parsed = JSON.parse(event.data) as { name: string; result: string };
                if (currentSteps.length > 0) {
                  const lastStep = currentSteps[currentSteps.length - 1]!;
                  lastStep.toolResult = parsed.result;
                  lastStep.isComplete = true;
                }
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last) {
                    updated[updated.length - 1] = {
                      ...last,
                      steps: [...currentSteps],
                    };
                  }
                  return updated;
                });
                break;
              }
              case "done": {
                // Mark all steps complete, set final content
                currentSteps.forEach((s) => (s.isComplete = true));
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last) {
                    updated[updated.length - 1] = {
                      ...last,
                      content: event.data,
                      steps: [...currentSteps],
                    };
                  }
                  return updated;
                });
                break;
              }
              case "trace": {
                const traceData = JSON.parse(event.data) as TraceData;
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last) {
                    updated[updated.length - 1] = { ...last, trace: traceData };
                  }
                  return updated;
                });
                break;
              }
              case "error": {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last) {
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + `\n\n**Error:** ${event.data}`,
                    };
                  }
                  return updated;
                });
                break;
              }
            }
          },
          controller.signal
        );
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last) {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + `\n\n**Error:** ${err.message}`,
              };
            }
            return updated;
          });
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [sessionId, isStreaming]
  );

  return { messages, isStreaming, send };
}
