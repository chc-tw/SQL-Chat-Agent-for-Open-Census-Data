from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, TypedDict

from app.agent.guardrails import check_guardrails
from app.agent.prompts import get_system_prompt
from app.agent.tools import TOOL_DISPATCH, TOOL_SCHEMAS
from app.services.anthropic_client import client

class _TraceIterationRequired(TypedDict):
    iteration: int


class TraceIteration(_TraceIterationRequired, total=False):
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


MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 10


async def run_agent(
    user_message: str,
    chat_history: list[dict[str, Any]] | None = None,
    max_iterations: int = MAX_ITERATIONS,
    # session_id and message_id are used to name the trace file and populate trace metadata
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
    # Guardrails check (async LLM-based)
    is_safe, rejection = await check_guardrails(user_message)
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

    trace_iterations: list[TraceIteration] = []

    for iteration in range(max_iterations):
        yield {"event": "step_start", "data": {"iteration": iteration}}
        current_trace_iter = TraceIteration(iteration=iteration)
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
                            current_trace_iter["thinking"] = current_trace_iter.get("thinking", "") + event.delta.text
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
                tool_trace = TraceIteration(
                    iteration=current_trace_iter["iteration"],
                    thinking=current_trace_iter.get("thinking", ""),
                    tool=tu["name"],
                    tool_input=parsed_inputs[tu["id"]],
                )

                # Dispatch tool (run sync tools in thread to avoid blocking event loop)
                dispatch_fn = TOOL_DISPATCH.get(tu["name"])
                if dispatch_fn:
                    result = await asyncio.to_thread(dispatch_fn, tool_input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {tu['name']}"})

                yield {"event": "tool_result", "data": {"name": tu["name"], "result": result}}
                tool_trace["tool_result"] = result
                trace_iterations.append(tool_trace)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn or max_tokens — we're done
        trace_iterations.append(current_trace_iter)
        break

    # If the loop exhausted max_iterations without a final answer, build an informative message
    if not full_response and trace_iterations:
        tools_used = [t.get("tool", "unknown") for t in trace_iterations if t.get("tool")]
        steps_summary = ", ".join(dict.fromkeys(tools_used)) or "various tools"
        full_response = (
            f"I was unable to produce a complete answer within the allowed number of steps. "
            f"Here is what I attempted:\n\n"
            f"I tried using: {steps_summary}.\n\n"
            f"The query may be too complex or the data may require a different approach. "
            f"Please try rephrasing your question or breaking it into smaller parts."
        )

    yield {"event": "done", "data": full_response}

    # Build trace
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
