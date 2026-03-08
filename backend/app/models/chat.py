from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    title: str = "New Chat"


class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: str


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str
    trace: str | None = None
