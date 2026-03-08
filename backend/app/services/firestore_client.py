from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud.firestore_v1 import AsyncClient

from app.settings import firestore_settings

db = AsyncClient(project=firestore_settings.project_id)


def _sessions_ref(username: str):
    return db.collection("users").document(username).collection("sessions")


async def create_session(username: str, title: str = "New Chat") -> dict[str, Any]:
    session_ref = _sessions_ref(username).document()
    data = {
        "title": title,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await session_ref.set(data)
    return {"session_id": session_ref.id, **data}


async def list_sessions(username: str) -> list[dict[str, Any]]:
    sessions_ref = _sessions_ref(username)
    docs = sessions_ref.order_by("created_at", direction="DESCENDING").stream()
    results = []
    async for doc in docs:
        d = doc.to_dict()
        results.append({"session_id": doc.id, **d})
    return results


async def get_session_messages(
    username: str, session_id: str
) -> list[dict[str, Any]]:
    messages_ref = (
        _sessions_ref(username)
        .document(session_id)
        .collection("messages")
        .order_by("timestamp")
    )
    results = []
    async for doc in messages_ref.stream():
        results.append(doc.to_dict())
    return results


async def delete_session(username: str, session_id: str) -> None:
    session_ref = _sessions_ref(username).document(session_id)
    # Delete all messages in the session
    messages_ref = session_ref.collection("messages")
    async for doc in messages_ref.stream():
        await doc.reference.delete()
    await session_ref.delete()


async def update_session_title(username: str, session_id: str, title: str) -> None:
    session_ref = _sessions_ref(username).document(session_id)
    await session_ref.update({"title": title})


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
