from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from app.agent.guardrails import check_guardrails
from app.agent.prompts import get_system_prompt
from app.agent.tools import TOOL_DISPATCH, TOOL_SCHEMAS
from app.services.anthropic_client import client

MODEL = "claude-sonnet-4-20250514"
MAX_ITERATIONS = 10


async def run_agent(
    user_message: str,
    chat_history: list[dict[str, Any]] | None = None,
    max_iterations: int = MAX_ITERATIONS,
    # session_id and message_id are used for trace collection (populated in Task 2)
    session_id: str | None = None,
    message_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Run the ReAct agent loop with streaming.

    Yields SSE-compatible event dicts:
        {"event": "step_start", "data": {"iteration": <int>}}
        {"event": "thinking_delta", "data": "<text chunk>"}
        {"event": "tool_use", "data": {"name": "...", "input": {...}}}
        {"event": "tool_result", "data": {"name": "...", "result": "..."}}
        {"event": "done", "data": "<full response text>"}
        {"event": "error", "data": "<error message>"}
    """
    # Guardrails check
    is_safe, rejection = check_guardrails(user_message)
    if not is_safe:
        yield {"event": "error", "data": rejection}
        yield {"event": "done", "data": rejection}
        return

    # Build messages array
    messages: list[dict[str, Any]] = []
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    system_prompt = get_system_prompt()
    full_response = ""

    for iteration in range(max_iterations):
        yield {"event": "step_start", "data": {"iteration": iteration}}
        # Stream the response
        collected_text = ""
        tool_uses: list[dict[str, Any]] = []
        stop_reason = None

        try:
            async with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=TOOL_SCHEMAS,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            tool_uses.append({
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            })
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            collected_text += event.delta.text
                            yield {"event": "thinking_delta", "data": event.delta.text}
                        elif event.delta.type == "input_json_delta":
                            if tool_uses:
                                tool_uses[-1]["input_json"] += event.delta.partial_json
                    elif event.type == "message_delta":
                        stop_reason = event.delta.stop_reason

        except Exception as e:
            yield {"event": "error", "data": str(e)}
            return

        # Build assistant message content blocks
        content_blocks: list[dict[str, Any]] = []
        if collected_text:
            content_blocks.append({"type": "text", "text": collected_text})
            if stop_reason != "tool_use":  # Only final answer goes into full_response
                full_response += collected_text

        parsed_inputs: dict[str, dict[str, Any]] = {}
        for tu in tool_uses:
            try:
                tool_input = json.loads(tu["input_json"]) if tu["input_json"] else {}
            except json.JSONDecodeError:
                tool_input = {}
            parsed_inputs[tu["id"]] = tool_input
            content_blocks.append({
                "type": "tool_use",
                "id": tu["id"],
                "name": tu["name"],
                "input": tool_input,
            })

        messages.append({"role": "assistant", "content": content_blocks})

        # If the model wants to use tools, execute them
        if stop_reason == "tool_use" and tool_uses:
            tool_results: list[dict[str, Any]] = []
            for tu in tool_uses:
                tool_input = parsed_inputs[tu["id"]]

                yield {"event": "tool_use", "data": {"name": tu["name"], "input": tool_input}}

                # Dispatch tool (run sync tools in thread to avoid blocking event loop)
                dispatch_fn = TOOL_DISPATCH.get(tu["name"])
                if dispatch_fn:
                    result = await asyncio.to_thread(dispatch_fn, tool_input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {tu['name']}"})

                yield {"event": "tool_result", "data": {"name": tu["name"], "result": result}}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn or max_tokens — we're done
        break

    yield {"event": "done", "data": full_response}
