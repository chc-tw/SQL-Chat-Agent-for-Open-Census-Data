# Auto-Rename Session Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-rename a chat session with a short LLM-generated title when the user sends their first message, updating the sidebar in real-time.

**Architecture:** On the first message of a session (`chat_history` is empty), `chat.py` starts an `asyncio.Task` for haiku title generation concurrently with the main agent loop. As agent events stream, the generator polls the title task; when it completes the generator yields a `session_rename` SSE event and updates Firestore. The frontend handles `session_rename` by calling an `onRename` callback that updates local session state — no re-fetch needed.

**Tech Stack:** Python asyncio, claude-haiku-4-5-20251001 (async Anthropic client), Firestore `.update()`, React `useCallback`, SSE

---

### Task 1: Add SESSION_TITLE_PROMPT to prompts.py

**Files:**
- Modify: `backend/app/agent/prompts.py`

**Step 1: Add the prompt constant**

Append to `prompts.py`:

```python
SESSION_TITLE_PROMPT = (
    "Generate a short title (3-6 words) for a chat session based on the user's first message. "
    "The title should be descriptive and specific — not generic like 'Census Data Query'. "
    "Examples: 'Population in Fulton County GA', 'Median Income San Diego 2019', "
    "'Education Attainment NYC vs LA'. "
    "Respond with ONLY the title text, no quotes, no punctuation at the end."
)
```

**Step 2: Verify import works**

```bash
cd backend && uv run python -c "from app.agent.prompts import SESSION_TITLE_PROMPT; print(SESSION_TITLE_PROMPT[:50])"
```
Expected: first 50 chars of the prompt printed.

**Step 3: Commit**

```bash
git add backend/app/agent/prompts.py
git commit -m "feat: add SESSION_TITLE_PROMPT for auto-rename"
```

---

### Task 2: Add update_session_title to firestore_client.py

**Files:**
- Modify: `backend/app/services/firestore_client.py`

**Step 1: Add the function**

After `delete_session`, add:

```python
async def update_session_title(username: str, session_id: str, title: str) -> None:
    session_ref = _sessions_ref(username).document(session_id)
    await session_ref.update({"title": title})
```

**Step 2: Verify import**

```bash
cd backend && uv run python -c "from app.services.firestore_client import update_session_title; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/services/firestore_client.py
git commit -m "feat: add update_session_title to firestore_client"
```

---

### Task 3: Add generate_session_title helper and wire into chat.py

**Files:**
- Modify: `backend/app/api/chat.py`

**Step 1: Add imports at top of chat.py**

Add to existing imports:
```python
import asyncio

from app.agent.prompts import SESSION_TITLE_PROMPT
from app.services.anthropic_client import client as anthropic_client
```

**Step 2: Add generate_session_title coroutine**

Add after the imports, before the router:

```python
_TITLE_MODEL = "claude-haiku-4-5-20251001"

async def generate_session_title(user_message: str) -> str:
    """Generate a short session title using haiku. Returns 'New Chat' on failure."""
    try:
        response = await anthropic_client.messages.create(
            model=_TITLE_MODEL,
            max_tokens=24,
            system=SESSION_TITLE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        title = response.content[0].text.strip()
        # Truncate to 60 chars as a safety limit
        return title[:60] if title else "New Chat"
    except Exception:
        return "New Chat"
```

**Step 3: Wire title generation into event_generator**

In `send_message`, modify `event_generator` to start a concurrent title task on first message and yield `session_rename` when ready.

Replace the `async def event_generator():` block with:

```python
    is_first_message = len(chat_history) == 0

    async def event_generator():
        message_id = str(uuid.uuid4())
        full_response = ""
        message_saved = False
        title_task: asyncio.Task | None = None
        title_emitted = False

        # Start title generation concurrently for first message only
        if is_first_message:
            title_task = asyncio.create_task(
                generate_session_title(request.content)
            )

        async for event in run_agent(
            request.content,
            chat_history,
            session_id=session_id,
            message_id=message_id,
        ):
            if event["event"] == "done":
                full_response = event["data"]
            elif event["event"] == "trace":
                trace_str = json.dumps(event["data"])
                await fs.add_message(
                    user.username, session_id, "assistant", full_response,
                    trace=trace_str,
                )
                message_saved = True

            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

            # Emit session_rename as soon as title is ready (non-blocking poll)
            if title_task and not title_emitted and title_task.done():
                title = title_task.result()
                await fs.update_session_title(user.username, session_id, title)
                yield {"event": "session_rename", "data": json.dumps(title)}
                title_emitted = True

        # Fallback: save without trace if trace event never fired
        if not message_saved and full_response:
            await fs.add_message(user.username, session_id, "assistant", full_response)

        # If title not emitted yet (haiku slower than agent), await and emit now
        if title_task and not title_emitted:
            title = await title_task
            await fs.update_session_title(user.username, session_id, title)
            yield {"event": "session_rename", "data": json.dumps(title)}
```

**Step 4: Verify backend starts**

```bash
cd backend && uv run python -c "from app.main import app; print('OK')"
```
Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: concurrent session title generation, yield session_rename SSE event"
```

---

### Task 4: Add session_rename to SSE types (frontend)

**Files:**
- Modify: `frontend/src/types/api.ts`

**Step 1: Add to SSEEvent union**

```typescript
export interface SSEEvent {
  event: "step_start" | "thinking_delta" | "tool_use" | "tool_result" | "done" | "trace" | "error" | "session_rename";
  data: string;
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm tsc --noEmit
```
Expected: no errors.

**Step 3: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat: add session_rename to SSEEvent union"
```

---

### Task 5: Handle session_rename in useChat.ts

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

**Step 1: Add onRename callback parameter**

Change the function signature:

```typescript
export function useChat(
  sessionId: string | null,
  onRename?: (sessionId: string, title: string) => void,
) {
```

**Step 2: Add session_rename case in the SSE switch**

After the `"error"` case, add:

```typescript
case "session_rename": {
  try {
    const title = JSON.parse(event.data) as string;
    if (sessionId && onRename) {
      onRename(sessionId, title);
    }
  } catch { /* malformed event, skip */ }
  break;
}
```

**Step 3: Verify TypeScript compiles**

```bash
cd frontend && pnpm tsc --noEmit
```
Expected: no errors.

**Step 4: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: handle session_rename SSE event in useChat"
```

---

### Task 6: Wire onRename into App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Add renameSession handler and pass to useChat**

In `ChatApp`, add a `renameSession` callback and pass it to `useChat`:

```typescript
const renameSession = useCallback(
  (sessionId: string, title: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.session_id === sessionId ? { ...s, title } : s))
    );
  },
  []
);

const { messages, isStreaming, send } = useChat(activeSessionId, renameSession);
```

Note: `setSessions` comes from `useSession` — it's not directly exposed. Instead, use the `reload` function OR add `renameSession` to `useSession`. The simplest approach: add `renameSession` to `useSession`.

**Step 2: Add renameSession to useSession.ts**

In `useSession.ts`, add inside the hook body:

```typescript
const renameSession = useCallback((sessionId: string, title: string) => {
  setSessions((prev) =>
    prev.map((s) => (s.session_id === sessionId ? { ...s, title } : s))
  );
}, []);
```

And return it:
```typescript
return {
  sessions,
  activeSessionId,
  setActiveSessionId,
  createSession,
  removeSession,
  renameSession,
  isLoading,
  reload: loadSessions,
};
```

**Step 3: Use renameSession in App.tsx**

```typescript
const {
  sessions,
  activeSessionId,
  setActiveSessionId,
  createSession,
  removeSession,
  renameSession,
} = useSession(!!username);

const { messages, isStreaming, send } = useChat(activeSessionId, renameSession);
```

**Step 4: Verify TypeScript compiles**

```bash
cd frontend && pnpm tsc --noEmit
```
Expected: no errors.

**Step 5: Commit**

```bash
git add frontend/src/hooks/useSession.ts frontend/src/App.tsx
git commit -m "feat: wire session auto-rename into sidebar via useSession"
```

---

### Task 7: End-to-end verification

**Step 1: Start backend**
```bash
cd backend && uv run uvicorn app.main:app --reload --port 8080
```

**Step 2: Start frontend**
```bash
cd frontend && pnpm dev
```

**Step 3: Manual test**
1. Create a new chat session — title shows "New Chat"
2. Send "Tell me the population of Fulton County, GA"
3. Within ~1s (while agent is still working): sidebar title should update to something like "Population Fulton County GA"
4. After response completes: title persists after page reload (Firestore confirmed)

**Step 4: Verify no regression on existing sessions**
- Switch to an existing session with messages — title unchanged
- Send a follow-up message — title unchanged (only first message triggers rename)
