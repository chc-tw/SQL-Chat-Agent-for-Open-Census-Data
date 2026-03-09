# Live Reasoning Steps & Agent Trace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace inline reasoning text with live collapsible step panels (like Gemini's thinking UI), and add persistent agent trace logs viewable in the UI.

**Architecture:** The backend SSE protocol gains two new event types (`step_start`, `thinking_delta`) replacing `text_delta`, plus a `trace` event emitted after `done`. The frontend assembles `ThinkingStep` objects per iteration and renders them as collapsible panels above the final answer. Trace JSON is written to a local file and persisted to Firestore so the "View Trace" button works after page reload.

**Tech Stack:** Python (TypedDict, asyncio), FastAPI SSE, Firestore AsyncClient, React 19, TypeScript, Tailwind CSS v4

---

## Task 1: Backend — Update SSE events in runner.py

**Files:**
- Modify: `backend/app/agent/runner.py`

**What changes:**
- Add `step_start` event at the top of each ReAct iteration
- Replace `yield {"event": "text_delta", ...}` with `yield {"event": "thinking_delta", ...}`
- Only accumulate `full_response` when `stop_reason == "end_turn"` (not for tool-use iterations)
- Accept two new optional params: `session_id: str | None = None`, `message_id: str | None = None` (needed for Task 2)

**Step 1: Read the current runner.py to understand the loop**

File: `backend/app/agent/runner.py` (already read above — the key loop is lines 48–136)

**Step 2: Update the function signature and loop**

Replace the current `run_agent` signature and loop body with:

```python
async def run_agent(
    user_message: str,
    chat_history: list[dict[str, Any]] | None = None,
    max_iterations: int = MAX_ITERATIONS,
    session_id: str | None = None,
    message_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Run the ReAct agent loop with streaming.

    Yields SSE-compatible event dicts:
        {"event": "step_start",     "data": {"iteration": N}}
        {"event": "thinking_delta", "data": "<text chunk>"}
        {"event": "tool_use",       "data": {"name": "...", "input": {...}}}
        {"event": "tool_result",    "data": {"name": "...", "result": "..."}}
        {"event": "done",           "data": "<full final response text>"}
        {"event": "trace",          "data": "<trace JSON string>"}
        {"event": "error",          "data": "<error message>"}
    """
```

Then inside the loop, at the top of `for iteration in range(max_iterations):`:

```python
    for iteration in range(max_iterations):
        yield {"event": "step_start", "data": {"iteration": iteration}}

        collected_text = ""
        tool_uses: list[dict[str, Any]] = []
        stop_reason = None
        ...
```

And change the `text_delta` yield inside the stream loop:

```python
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            collected_text += event.delta.text
                            yield {"event": "thinking_delta", "data": event.delta.text}  # was text_delta
```

And only accumulate `full_response` when it's a final turn:

```python
        # After the stream loop — only add to full_response if this is the final answer
        content_blocks: list[dict[str, Any]] = []
        if collected_text:
            content_blocks.append({"type": "text", "text": collected_text})
            if stop_reason != "tool_use":          # <-- only final iteration contributes
                full_response += collected_text
```

**Step 3: Verify backend still imports cleanly**

```bash
cd backend && uv run python -c "from app.agent.runner import run_agent; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add backend/app/agent/runner.py
git commit -m "feat: add step_start + thinking_delta SSE events, fix full_response accumulation"
```

---

## Task 2: Backend — Add trace collection and emission in runner.py

**Files:**
- Modify: `backend/app/agent/runner.py`
- Create: `backend/traces/.gitkeep` (the traces/ directory)

**What changes:**
- Add `TraceIteration` and `TraceData` TypedDicts
- Collect trace data during the agent loop
- After `done`, write JSON to `backend/traces/{session_id}_{message_id}.json`
- Emit `{"event": "trace", "data": "<json string>"}` after `done`

**Step 1: Add TypedDicts at the top of runner.py (after imports)**

```python
from typing import Any, AsyncGenerator, TypedDict
import os
from datetime import datetime, timezone
from pathlib import Path


class TraceIteration(TypedDict, total=False):
    iteration: int
    thinking: str
    tool: str
    tool_input: dict[str, Any]
    tool_result: str


class TraceData(TypedDict):
    session_id: str
    message_id: str
    user_message: str
    timestamp: str
    iterations: list[TraceIteration]
    final_response: str
```

**Step 2: Initialize trace collector before the loop**

```python
    trace_iterations: list[TraceIteration] = []
    current_trace_iter: TraceIteration = {}
```

**Step 3: Populate trace data inside the loop**

At the top of the iteration (after `yield step_start`):
```python
        current_trace_iter = TraceIteration(iteration=iteration, thinking="")
```

When collecting thinking text (after `collected_text += event.delta.text`):
```python
                            current_trace_iter["thinking"] = current_trace_iter.get("thinking", "") + event.delta.text
```

When dispatching a tool (inside `for tu in tool_uses:`):
```python
                yield {"event": "tool_use", "data": {"name": tu["name"], "input": tool_input}}
                current_trace_iter["tool"] = tu["name"]
                current_trace_iter["tool_input"] = tool_input
```

After getting tool result:
```python
                yield {"event": "tool_result", "data": {"name": tu["name"], "result": result}}
                current_trace_iter["tool_result"] = result
                trace_iterations.append(current_trace_iter)
```

For end_turn iterations (no tool use), append the trace iter after the loop:
```python
        # After break (end_turn)
        if stop_reason != "tool_use":
            trace_iterations.append(current_trace_iter)
        break
```

Wait — the current code does `continue` for tool_use and `break` for end_turn. Restructure so trace is appended in both paths:

```python
        if stop_reason == "tool_use" and tool_uses:
            tool_results = []
            for tu in tool_uses:
                ...dispatch...
                current_trace_iter["tool"] = tu["name"]
                current_trace_iter["tool_input"] = tool_input
                current_trace_iter["tool_result"] = result
            trace_iterations.append(current_trace_iter)
            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn
        trace_iterations.append(current_trace_iter)
        break
```

**Step 4: Emit done + write trace + emit trace**

Replace the final `yield done` with:

```python
    yield {"event": "done", "data": full_response}

    # Build and emit trace
    trace: TraceData = {
        "session_id": session_id or "",
        "message_id": message_id or "",
        "user_message": user_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "iterations": trace_iterations,
        "final_response": full_response,
    }
    trace_json = json.dumps(trace, ensure_ascii=False)

    # Write to local file for debugging
    if session_id and message_id:
        traces_dir = Path(__file__).parent.parent.parent / "traces"
        traces_dir.mkdir(exist_ok=True)
        trace_file = traces_dir / f"{session_id}_{message_id}.json"
        trace_file.write_text(trace_json, encoding="utf-8")

    yield {"event": "trace", "data": trace_json}
```

**Step 5: Create traces directory with .gitkeep**

```bash
mkdir -p backend/traces && touch backend/traces/.gitkeep
```

**Step 6: Add traces/ to .gitignore (but keep .gitkeep)**

Add to `.gitignore`:
```
backend/traces/*.json
```

**Step 7: Verify**

```bash
cd backend && uv run python -c "from app.agent.runner import run_agent, TraceData; print('OK')"
```

Expected: `OK`

**Step 8: Commit**

```bash
git add backend/app/agent/runner.py backend/traces/.gitkeep .gitignore
git commit -m "feat: add trace collection and trace SSE event to agent runner"
```

---

## Task 3: Backend — Add trace field to MessageResponse model

**Files:**
- Modify: `backend/app/models/chat.py`

**Step 1: Add optional trace field**

```python
class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str
    trace: str | None = None
```

**Step 2: Verify**

```bash
cd backend && uv run python -c "from app.models.chat import MessageResponse; m = MessageResponse(role='assistant', content='hi', timestamp='now'); print(m.trace)"
```

Expected: `None`

**Step 3: Commit**

```bash
git add backend/app/models/chat.py
git commit -m "feat: add optional trace field to MessageResponse model"
```

---

## Task 4: Backend — Update Firestore client to persist trace

**Files:**
- Modify: `backend/app/services/firestore_client.py`

**Step 1: Update `add_message` to accept optional trace**

```python
async def add_message(
    username: str,
    session_id: str,
    role: str,
    content: str,
    trace: str | None = None,
) -> dict[str, Any]:
    messages_ref = (
        _sessions_ref(username).document(session_id).collection("messages")
    )
    data: dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if trace is not None:
        data["trace"] = trace
    await messages_ref.add(data)
    return data
```

**Step 2: Update `get_session_messages` to include trace**

The current code already does `doc.to_dict()` which returns all fields including `trace` if present. No change needed — Firestore returns all stored fields automatically.

**Step 3: Verify**

```bash
cd backend && uv run python -c "from app.services.firestore_client import add_message; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add backend/app/services/firestore_client.py
git commit -m "feat: add optional trace param to firestore add_message"
```

---

## Task 5: Backend — Update chat.py to pass IDs and handle trace event

**Files:**
- Modify: `backend/app/api/chat.py`

**What changes:**
- Generate a `message_id` UUID before calling `run_agent`
- Pass `session_id` and `message_id` to `run_agent`
- On `trace` event: save assistant message with both `full_response` and trace JSON
- Remove saving on `done` (deferred until `trace` arrives; fallback saves on done if trace never comes)

**Step 1: Add uuid import**

```python
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
```

**Step 2: Rewrite `event_generator` in `send_message`**

```python
    async def event_generator():
        message_id = str(uuid.uuid4())
        full_response = ""
        message_saved = False

        async for event in run_agent(
            request.content,
            chat_history,
            session_id=session_id,
            message_id=message_id,
        ):
            if event["event"] == "done":
                full_response = event["data"]
            elif event["event"] == "trace":
                # Save assistant message with trace attached
                await fs.add_message(
                    user.username, session_id, "assistant", full_response,
                    trace=event["data"],
                )
                message_saved = True

            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]) if not isinstance(event["data"], str) else event["data"],
            }

        # Fallback: save without trace if trace event never fired (e.g., guardrail rejection)
        if not message_saved and full_response:
            await fs.add_message(user.username, session_id, "assistant", full_response)
```

**Step 3: Verify import**

```bash
cd backend && uv run python -c "from app.api.chat import router; print('OK')"
```

Expected: `OK`

**Step 4: Verify full app import**

```bash
cd backend && uv run python -c "from app.main import app; print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: pass session/message IDs to run_agent, save trace to Firestore"
```

---

## Task 6: Frontend — Update types (ui.ts and api.ts)

**Files:**
- Modify: `frontend/src/types/ui.ts`
- Modify: `frontend/src/types/api.ts`

**Step 1: Replace ui.ts entirely**

```typescript
export interface ThinkingStep {
  thinking: string;        // live reasoning text (streams in char by char)
  toolName?: string;       // set when tool_use event fires
  toolInput?: unknown;
  toolResult?: string;     // set when tool_result event fires
  isComplete: boolean;     // true once tool_result received or end_turn reached
}

export interface TraceIteration {
  iteration: number;
  thinking: string;
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
```

**Step 2: Update api.ts — SSEEvent union and MessageResponse**

Change:
```typescript
export interface MessageResponse {
  role: string;
  content: string;
  timestamp: string;
  trace?: string;  // JSON string, parsed on load
}

export interface SSEEvent {
  event: "step_start" | "thinking_delta" | "tool_use" | "tool_result" | "done" | "trace" | "error";
  data: string;
}
```

**Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: errors only about imports from useChat.ts (which we'll fix in Task 7). No errors in types files themselves.

**Step 4: Commit**

```bash
git add frontend/src/types/ui.ts frontend/src/types/api.ts
git commit -m "feat: add ThinkingStep, TraceData types; update SSEEvent union"
```

---

## Task 7: Frontend — Update useChat.ts for new SSE events

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

**What changes:**
- Remove standalone `steps` state (steps now live on each `ChatMessage`)
- Handle `step_start` → push new ThinkingStep
- Handle `thinking_delta` → append to last step's thinking
- Handle `tool_use` → update last step with toolName/toolInput
- Handle `tool_result` → update last step with toolResult + isComplete=true
- Handle `done` → set message content from event.data
- Handle `trace` → parse JSON, attach to last assistant message
- On session history load: parse `trace` JSON string → `TraceData` object

**Step 1: Write the new useChat.ts**

```typescript
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
                  currentSteps[currentSteps.length - 1].thinking += event.data;
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
                const parsed = JSON.parse(event.data);
                if (currentSteps.length > 0) {
                  currentSteps[currentSteps.length - 1].toolName = parsed.name;
                  currentSteps[currentSteps.length - 1].toolInput = parsed.input;
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
                const parsed = JSON.parse(event.data);
                if (currentSteps.length > 0) {
                  currentSteps[currentSteps.length - 1].toolResult = parsed.result;
                  currentSteps[currentSteps.length - 1].isComplete = true;
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
```

Note: `steps` is no longer returned from `useChat` — it's embedded in each `ChatMessage`.

**Step 2: Update App.tsx if it uses `steps` from useChat**

Check `frontend/src/App.tsx` — the current code destructures `{ messages, isStreaming, send }` from `useChat`. No change needed there.

**Step 3: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors (or only errors in MessageBubble which we'll fix next)

**Step 4: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: update useChat to handle step_start, thinking_delta, trace SSE events"
```

---

## Task 8: Frontend — Build ThinkingStepsPanel in MessageBubble.tsx

**Files:**
- Modify: `frontend/src/components/chat/MessageBubble.tsx`

**What changes:**
Replace the simple `<details>` with a proper `ThinkingStepsPanel` that renders above the final answer. Each step shows:
- Sparkle icon (animated while active, static when complete)
- Friendly tool label
- Chevron toggle
- Expanded: reasoning text in italic

**Step 1: Write the new MessageBubble.tsx**

```tsx
import { useState } from "react";
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
  const [expanded, setExpanded] = useState(!step.isComplete);
  const label = step.toolName ? (TOOL_LABELS[step.toolName] ?? step.toolName) : "Thinking...";

  return (
    <div className="mb-1">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 w-full text-left px-2 py-1 rounded hover:bg-gray-100 transition-colors"
      >
        {/* Sparkle icon — animated when active */}
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
                {message.content || (message.steps && message.steps.length > 0 ? "" : "Thinking...")}
              </Markdown>
            </div>

            {/* Trace panel */}
            {message.trace && <TracePanel trace={message.trace} />}
          </>
        )}
      </div>
    </div>
  );
}
```

Key behaviors:
- Active steps (`isComplete=false`) auto-expand and show the sparkle pulse animation
- Completed steps collapse by default (user can click to re-expand)
- "Thinking..." label shows before `tool_use` event arrives
- Tool label updates once `tool_use` event fires (toolName is set)

**Step 2: Check TypeScript (will error on TracePanel import until Task 9)**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -v TracePanel | head -20
```

**Step 3: Commit (after Task 9 completes, or stub TracePanel now)**

Hold off on commit until TracePanel exists.

---

## Task 9: Frontend — Build TracePanel.tsx

**Files:**
- Create: `frontend/src/components/chat/TracePanel.tsx`

**What it does:**
- A "View Trace" button below the response
- Expands inline to show structured trace data grouped by tool type

**Step 1: Create TracePanel.tsx**

```tsx
import { useState } from "react";
import type { TraceData, TraceIteration } from "../../types/ui";

interface TracePanelProps {
  trace: TraceData;
}

function CodeBlock({ code }: { code: string }) {
  return (
    <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-2 overflow-x-auto whitespace-pre-wrap break-words">
      {code}
    </pre>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
        {title}
      </h4>
      {children}
    </div>
  );
}

function FipsSection({ iterations }: { iterations: TraceIteration[] }) {
  const fipsIters = iterations.filter((i) => i.tool === "search_fips_codes");
  if (fipsIters.length === 0) return null;
  return (
    <Section title="FIPS Resolution">
      {fipsIters.map((iter, i) => (
        <div key={i} className="mb-2">
          <p className="text-xs text-gray-600 mb-1">
            Query: <span className="font-mono">{JSON.stringify(iter.tool_input)}</span>
          </p>
          <CodeBlock code={iter.tool_result ?? ""} />
        </div>
      ))}
    </Section>
  );
}

function FeatureSearchSection({ iterations }: { iterations: TraceIteration[] }) {
  const iters = iterations.filter((i) => i.tool === "search_feature_schema");
  if (iters.length === 0) return null;
  return (
    <Section title="Feature Search">
      {iters.map((iter, i) => (
        <div key={i} className="mb-2">
          <p className="text-xs text-gray-600 mb-1">
            Query: <span className="font-mono">{JSON.stringify(iter.tool_input)}</span>
          </p>
          <CodeBlock code={iter.tool_result ?? ""} />
        </div>
      ))}
    </Section>
  );
}

function FieldDescSection({ iterations }: { iterations: TraceIteration[] }) {
  const iters = iterations.filter((i) => i.tool === "get_field_descriptions");
  if (iters.length === 0) return null;
  return (
    <Section title="Field Descriptions">
      {iters.map((iter, i) => (
        <div key={i} className="mb-2">
          <p className="text-xs text-gray-600 mb-1">
            Table: <span className="font-mono">{JSON.stringify(iter.tool_input)}</span>
          </p>
          <CodeBlock code={iter.tool_result ?? ""} />
        </div>
      ))}
    </Section>
  );
}

function SqlSection({ iterations }: { iterations: TraceIteration[] }) {
  const iters = iterations.filter((i) => i.tool === "execute_sql");
  if (iters.length === 0) return null;
  return (
    <Section title="SQL Query">
      {iters.map((iter, i) => (
        <div key={i} className="mb-3">
          <p className="text-xs text-gray-500 mb-1">Query:</p>
          <CodeBlock code={(iter.tool_input as { sql?: string })?.sql ?? JSON.stringify(iter.tool_input)} />
          <p className="text-xs text-gray-500 mt-2 mb-1">Result (truncated):</p>
          <CodeBlock code={iter.tool_result ?? ""} />
        </div>
      ))}
    </Section>
  );
}

function ReasoningSection({ iterations }: { iterations: TraceIteration[] }) {
  const withThinking = iterations.filter((i) => i.thinking?.trim());
  if (withThinking.length === 0) return null;
  return (
    <Section title="Reasoning">
      {withThinking.map((iter) => (
        <div key={iter.iteration} className="mb-2">
          <p className="text-xs text-gray-400 mb-0.5">Step {iter.iteration + 1}</p>
          <p className="text-xs italic text-gray-600 whitespace-pre-wrap">{iter.thinking}</p>
        </div>
      ))}
    </Section>
  );
}

export function TracePanel({ trace }: TracePanelProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3 border-t border-gray-100 pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        {open ? "Hide Trace ▲" : "View Trace ▼"}
      </button>
      {open && (
        <div className="mt-2 space-y-0">
          <FipsSection iterations={trace.iterations} />
          <FeatureSearchSection iterations={trace.iterations} />
          <FieldDescSection iterations={trace.iterations} />
          <SqlSection iterations={trace.iterations} />
          <ReasoningSection iterations={trace.iterations} />
        </div>
      )}
    </div>
  );
}
```

**Step 2: Full TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

**Step 3: Commit both MessageBubble and TracePanel together**

```bash
git add frontend/src/components/chat/MessageBubble.tsx frontend/src/components/chat/TracePanel.tsx
git commit -m "feat: add ThinkingStepsPanel with live reasoning and TracePanel with View Trace button"
```

---

## Task 10: Verification

**Step 1: Backend smoke test**

```bash
cd backend && uv run python -c "from app.main import app; print('Backend OK')"
```

Expected: `Backend OK`

**Step 2: Frontend TypeScript check**

```bash
cd frontend && npx tsc --noEmit && echo "Frontend OK"
```

Expected: `Frontend OK`

**Step 3: Start both services and manual E2E test**

Terminal 1 (backend):
```bash
cd backend && uv run uvicorn app.main:app --reload --port 8080
```

Terminal 2 (frontend):
```bash
cd frontend && pnpm dev
```

Open browser → login → ask: "What is the total population of Fulton County, Georgia in 2019?"

**Verify:**
- [ ] Steps appear above the response area while the agent works
- [ ] Each step shows "Thinking..." with pulse animation, then updates to friendly label ("Searching for locations") when tool fires
- [ ] Reasoning text streams live inside the expanded step
- [ ] Completed steps collapse (can click to re-expand)
- [ ] Final answer appears cleanly below all steps once done
- [ ] "View Trace" button appears below the answer
- [ ] Trace panel shows FIPS resolution, SQL query, SQL result
- [ ] Reload the page → "View Trace" still works on previous messages
- [ ] `backend/traces/` contains a JSON file for the conversation

**Step 4: Final commit if any cleanup needed**

```bash
git add -p
git commit -m "chore: post-verification cleanup"
```
