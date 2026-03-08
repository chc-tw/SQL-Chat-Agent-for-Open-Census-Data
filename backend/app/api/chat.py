from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.agent.runner import run_agent
from app.models.auth import UserInfo
from app.models.chat import CreateSessionRequest, MessageRequest, MessageResponse, SessionInfo
from app.services.auth import get_current_user
from app.services import firestore_client as fs

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
    # Save user message
    await fs.add_message(user.username, session_id, "user", request.content)

    # Load chat history
    history = await fs.get_session_messages(user.username, session_id)
    # Exclude the just-added user message (it's passed separately to the agent)
    chat_history = [
        {"role": m["role"], "content": m["content"]}
        for m in history[:-1]
    ]

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
            # "trace" is always emitted after "done" by run_agent (see runner.py)
            elif event["event"] == "trace":
                # Save assistant message with trace attached
                trace_str = json.dumps(event["data"]) if not isinstance(event["data"], str) else event["data"]
                await fs.add_message(
                    user.username, session_id, "assistant", full_response,
                    trace=trace_str,
                )
                message_saved = True

            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]) if not isinstance(event["data"], str) else event["data"],
            }

        # Fallback: save without trace if trace event never fired
        if not message_saved and full_response:
            await fs.add_message(user.username, session_id, "assistant", full_response)

    return EventSourceResponse(event_generator())
