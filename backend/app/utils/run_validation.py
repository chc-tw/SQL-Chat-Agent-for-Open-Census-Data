from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

TESTCASE_PATH = Path(__file__).resolve().parents[3] / "Dataset" / "testcase.json"
QUESTIONS_PER_LEVEL = 3
LEVELS = ("easy", "medium", "hard")


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

async def _iter_sse(response: httpx.Response) -> AsyncGenerator[dict[str, Any], None]:
    """Parse a raw SSE stream into (event, data) dicts."""
    current_event = "message"
    current_data: list[str] = []

    async for raw_line in response.aiter_lines():
        line = raw_line.strip()
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            current_data.append(line[5:].strip())
        elif line == "":
            if current_data:
                raw = "\n".join(current_data)
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = raw
                yield {"event": current_event, "data": data}
            current_event = "message"
            current_data = []


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


async def create_session(client: httpx.AsyncClient, title: str = "New Chat") -> str:
    resp = await client.post("/api/chat/sessions", json={"title": title})
    resp.raise_for_status()
    return resp.json()["session_id"]


async def delete_session(client: httpx.AsyncClient, session_id: str) -> None:
    resp = await client.delete(f"/api/chat/sessions/{session_id}")
    resp.raise_for_status()


async def send_message(
    client: httpx.AsyncClient,
    session_id: str,
    content: str,
    label: str,
) -> tuple[str, dict | None]:
    """
    Stream a message to the server, print events live, and return
    (full_response_text, trace_dict).
    """
    full_response = ""
    trace: dict | None = None

    print(f"\n  [{label}] {content}")
    print(f"  {'─' * 66}")

    async with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/messages",
        json={"content": content},
        timeout=300.0,
    ) as response:
        response.raise_for_status()

        async for sse in _iter_sse(response):
            event_type = sse["event"]
            data = sse["data"]

            if event_type == "step_start":
                iteration = data.get("iteration", 0)
                print(f"\n  ── step {iteration + 1} ──", flush=True)

            elif event_type == "thinking_delta":
                print(data, end="", flush=True)

            elif event_type == "tool_use":
                args_preview = json.dumps(data.get("input", {}))[:120]
                print(f"\n  → {data['name']}({args_preview})", flush=True)

            elif event_type == "tool_result":
                preview = str(data.get("result", ""))[:140].replace("\n", " ")
                print(f"  ← {preview}", flush=True)

            elif event_type == "done":
                full_response = data
                preview = full_response[:200]
                suffix = "…" if len(full_response) > 200 else ""
                print(f"\n\n  [done] {preview}{suffix}", flush=True)

            elif event_type == "trace":
                trace = data

            elif event_type == "session_rename":
                print(f"\n  [renamed → {data}]", flush=True)

            elif event_type == "error":
                print(f"\n  [ERROR] {data}", flush=True)

    return full_response, trace


# ---------------------------------------------------------------------------
# Test case runner
# ---------------------------------------------------------------------------

async def run_case(
    client: httpx.AsyncClient,
    level: str,
    case: dict,
    case_num: int,
    total: int,
) -> dict[str, Any]:
    case_id = case["id"]
    question = case["question"]
    follow_up = case["follow_up_question"]

    print(f"\n{'═' * 70}")
    print(f"  [{case_num}/{total}]  level={level.upper()}  id={case_id}")
    print(f"{'═' * 70}")

    session_id = await create_session(client, f"Validation {level}-{case_id}")

    response1, trace1 = await send_message(client, session_id, question, "Q")
    response2, trace2 = await send_message(client, session_id, follow_up, "F")

    await delete_session(client, session_id)
    print(f"\n  [session {session_id[:8]} deleted from Firestore]", flush=True)

    return {
        "level": level,
        "case_id": case_id,
        "session_id": session_id,
        "question": question,
        "follow_up": follow_up,
        "r1_len": len(response1),
        "r2_len": len(response2),
        "t1_ms": trace1.get("duration_ms") if trace1 else None,
        "t2_ms": trace2.get("duration_ms") if trace2 else None,
        "t1_tokens_in": trace1.get("input_tokens") if trace1 else None,
        "t1_tokens_out": trace1.get("output_tokens") if trace1 else None,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(url: str, username: str, password: str, seed: int | None) -> None:
    if not TESTCASE_PATH.exists():
        print(f"Error: testcase.json not found at {TESTCASE_PATH}", file=sys.stderr)
        sys.exit(1)

    test_cases: dict[str, list] = json.loads(TESTCASE_PATH.read_text(encoding="utf-8"))

    rng = random.Random(seed)
    selected: dict[str, list] = {}
    for level in LEVELS:
        pool = test_cases.get(level, [])
        n = min(QUESTIONS_PER_LEVEL, len(pool))
        selected[level] = rng.sample(pool, n)

    total = sum(len(v) for v in selected.values())

    print(f"Validation run  url={url}  user={username}  seed={seed}  cases={total}")
    for level, cases in selected.items():
        ids = [c["id"] for c in cases]
        print(f"  {level:6}: IDs {ids}")

    async with httpx.AsyncClient(base_url=url, timeout=300.0) as client:
        token = await login(client, username, password)
        client.headers["Authorization"] = f"Bearer {token}"
        print(f"\nAuthenticated as '{username}' ✓")

        tasks = []
        case_num = 0
        for level, cases in selected.items():
            for case in cases:
                case_num += 1
                tasks.append(run_case(client, level, case, case_num, total))

        results: list[dict] = await asyncio.gather(*tasks)

    # Summary table
    print(f"\n{'═' * 70}")
    print("  SUMMARY")
    print(f"{'═' * 70}")
    header = f"  {'Level':6}  {'ID':>3}  {'Q chars':>7}  {'Q ms':>8}  {'Q in/out tok':>14}  {'F chars':>7}  {'F ms':>8}"
    print(header)
    print(f"  {'─' * 66}")
    for r in results:
        t1 = f"{r['t1_ms']}ms" if r["t1_ms"] is not None else "N/A"
        t2 = f"{r['t2_ms']}ms" if r["t2_ms"] is not None else "N/A"
        tok = (
            f"{r['t1_tokens_in']}/{r['t1_tokens_out']}"
            if r["t1_tokens_in"] is not None
            else "N/A"
        )
        print(
            f"  {r['level']:6}  {r['case_id']:>3}  "
            f"{r['r1_len']:>7}  {t1:>8}  {tok:>14}  "
            f"{r['r2_len']:>7}  {t2:>8}"
        )
    print(f"\n  Trace files → backend/traces/")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Validation runner for Census Chat Agent")
    parser.add_argument("--url", default="http://localhost:8080", help="API base URL")
    parser.add_argument("--username", default="admin", help="Login username")
    parser.add_argument("--password", default="admin", help="Login password")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible selection")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.username, args.password, args.seed))


if __name__ == "__main__":
    cli()
