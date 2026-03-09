from __future__ import annotations

from app.agent.prompts import GUARDRAIL_SYSTEM_PROMPT
from app.services.anthropic_client import client

GUARDRAIL_MODEL = "claude-haiku-4-5-20251001"


async def check_guardrails(
    user_message: str,
    chat_history: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Check whether a user message is appropriate using claude-haiku-4-5.

    Pass chat_history (list of {role, content} dicts) to give context for
    follow-up questions that look ambiguous in isolation.

    Returns:
        (is_safe, rejection_message) — if is_safe is False, rejection_message
        explains why the message was blocked.
    """
    # Build context string from the last 3 conversation turns (6 messages)
    eval_message = user_message
    if chat_history:
        recent = chat_history[-6:]
        lines = [
            f"{m['role'].capitalize()}: {m['content'][:300]}"
            for m in recent
        ]
        context = "Recent conversation:\n" + "\n".join(lines)
        eval_message = f"{context}\n\nNew message to evaluate: {user_message}"

    try:
        response = await client.messages.create(
            model=GUARDRAIL_MODEL,
            max_tokens=60,
            system=GUARDRAIL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": eval_message}],
        )
        text = response.content[0].text.strip()

        if text.startswith("BLOCK"):
            parts = text.split("|", 1)
            reason = parts[1].strip() if len(parts) > 1 else (
                "I can only help with questions about US Census data."
            )
            return False, reason

        return True, ""

    except Exception:
        # Fail open — if the guardrail check itself errors, allow the request
        # so a transient API issue doesn't block legitimate users.
        return True, ""
