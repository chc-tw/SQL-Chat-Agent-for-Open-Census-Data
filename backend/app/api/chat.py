from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.agent.guardrails import check_guardrails
from app.agent.prompts import SESSION_TITLE_PROMPT
from app.agent.runner import run_agent
from app.models.auth import UserInfo
from app.models.chat import CreateSessionRequest, MessageRequest, MessageResponse, SessionInfo
from app.services.anthropic_client import client as anthropic_client
from app.services.auth import get_current_user
from app.services import firestore_client as fs

_TITLE_MODEL = "claude-haiku-4-5-20251001"
_TRACES_DIR = Path(__file__).parent.parent.parent / "traces"


def _sanitize_filename(title: str) -> str:
    """Convert a session title into a safe filename component."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    return slug[:40] or "new_chat"


def _append_trace_to_file(trace: dict, session_id: str, title: str) -> None:
    """Append a trace dict to traces/{title}_{short_id}.json (JSON array per session)."""
    try:
        _TRACES_DIR.mkdir(exist_ok=True)
        short_id = session_id[:8]
        trace_file = _TRACES_DIR / f"{_sanitize_filename(title)}_{short_id}.json"
        existing: list = []
        if trace_file.exists():
            try:
                parsed = json.loads(trace_file.read_text(encoding="utf-8"))
                existing = parsed if isinstance(parsed, list) else [parsed]
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.append(trace)
        trace_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass  # trace file writing is best-effort for local debug


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
        return title[:60] if title else "New Chat"
    except Exception:
        return "New Chat"


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", response_model=SessionInfo)
async def create_session(
    request: CreateSessionRequest,
    user: UserInfo = Depends(get_current_user),
):
    session = await fs.create_session(user.username, request.title)
    return SessionInfo(**session)


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(user: UserInfo = Depends(get_current_user)):
    sessions = await fs.list_sessions(user.username)
    return [SessionInfo(**s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
):
    messages = await fs.get_session_messages(user.username, session_id)
    return [MessageResponse(**m) for m in messages]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
):
    await fs.delete_session(user.username, session_id)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: MessageRequest,
    user: UserInfo = Depends(get_current_user),
):
    # Load history BEFORE saving so guardrails can see conversation context
    history = await fs.get_session_messages(user.username, session_id)
    chat_history = [
        {"role": m["role"], "content": m["content"]}
        for m in history
    ]

    # Guardrails check — pass history for follow-up context awareness
    is_safe, rejection = await check_guardrails(request.content, chat_history)
    if not is_safe:
        async def blocked_generator():
            yield {"event": "error", "data": json.dumps(rejection)}
            yield {"event": "done", "data": json.dumps(rejection)}
        return EventSourceResponse(blocked_generator())

    # Only persist the user message after guardrails pass
    await fs.add_message(user.username, session_id, "user", request.content)

    is_first_message = len(chat_history) == 0

    # Fetch current session title for trace filename (existing sessions already have one)
    session_data = await fs.get_session(user.username, session_id)
    current_title = session_data.get("title", "New Chat")

    async def event_generator():
        message_id = str(uuid.uuid4())
        full_response = ""
        message_saved = False
        title_task: asyncio.Task | None = None
        title_emitted = False
        resolved_title = current_title  # updated if title_task resolves
        buffered_trace: dict | None = None

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
                buffered_trace = event["data"]
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
                resolved_title = title_task.result()
                await fs.update_session_title(user.username, session_id, resolved_title)
                yield {"event": "session_rename", "data": json.dumps(resolved_title)}
                title_emitted = True

        # Fallback: save without trace if trace event never fired
        if not message_saved and full_response:
            await fs.add_message(user.username, session_id, "assistant", full_response)

        # If title not emitted yet (haiku slower than agent), await and emit now
        if title_task and not title_emitted:
            resolved_title = await title_task
            await fs.update_session_title(user.username, session_id, resolved_title)
            yield {"event": "session_rename", "data": json.dumps(resolved_title)}

        # Append trace to per-session file (uses resolved title for readable filename)
        if buffered_trace and session_id:
            _append_trace_to_file(buffered_trace, session_id, resolved_title)

    return EventSourceResponse(event_generator())
