"""Timed end-to-end test client — đo LATENCY của Stage 5.

Gửi 1 câu hỏi tới Customer Agent, đo tổng thời gian từ lúc gửi đến lúc nhận
được câu trả lời đầy đủ (đi qua: customer -> law -> [tax || compliance] -> aggregate).

Chạy (sau khi đã start_all):
    uv run python test_client_timed.py
"""

import asyncio
import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

CUSTOMER_AGENT_URL = os.getenv("CUSTOMER_AGENT_URL", "http://localhost:10100")

QUESTION = (
    "If a company breaks a contract and avoids taxes, "
    "what are the legal and regulatory consequences?"
)


async def run_once(http_client) -> tuple[float, str]:
    """Gửi 1 request, trả về (latency_giây, response_text)."""
    from a2a.types import (
        AgentCard, Message, Part, Role, TextPart,
        SendMessageRequest, MessageSendParams,
    )
    from a2a.client import A2AClient
    from uuid import uuid4

    card_url = f"{CUSTOMER_AGENT_URL}/.well-known/agent.json"
    card_resp = await http_client.get(card_url)
    card_resp.raise_for_status()
    agent_card = AgentCard.model_validate(card_resp.json())

    client = A2AClient(httpx_client=http_client, agent_card=agent_card)
    message = Message(
        role=Role.user,
        parts=[Part(root=TextPart(text=QUESTION))],
        message_id=str(uuid4()),
    )
    request = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(message=message))

    # ----- ĐO LATENCY -----
    t0 = time.perf_counter()
    response = await client.send_message(request)
    latency = time.perf_counter() - t0

    # Trích text
    result_text = ""
    root = getattr(response, "root", response)
    result = getattr(root, "result", None)
    if result is not None:
        artifacts = getattr(result, "artifacts", None)
        if artifacts:
            for artifact in artifacts:
                for part in artifact.parts:
                    p = getattr(part, "root", part)
                    result_text += getattr(p, "text", "") or ""
        if not result_text:
            parts = getattr(result, "parts", None) or []
            for part in parts:
                p = getattr(part, "root", part)
                result_text += getattr(p, "text", "") or ""
    return latency, result_text


async def main() -> None:
    runs = int(os.getenv("TIMED_RUNS", "1"))
    label = os.getenv("TIMED_LABEL", "BASELINE")

    print("=" * 64)
    print(f"  ĐO LATENCY STAGE 5 — {label}")
    print("=" * 64)
    print(f"Customer Agent: {CUSTOMER_AGENT_URL}")
    print(f"Question: {QUESTION}")
    print(f"Số lần chạy: {runs}")
    print("-" * 64)

    latencies = []
    async with httpx.AsyncClient(timeout=300.0) as http_client:
        # health check
        try:
            await http_client.get(f"{CUSTOMER_AGENT_URL}/.well-known/agent.json")
        except Exception as e:
            print(f"ERROR: không kết nối được Customer Agent: {e}")
            sys.exit(1)

        for i in range(1, runs + 1):
            latency, text = await run_once(http_client)
            latencies.append(latency)
            print(f"[Run {i}] Latency = {latency:.2f} s | response {len(text)} ký tự")
            if i == 1:
                print("\n--- Trích đoạn câu trả lời ---")
                print(text[:400] + ("..." if len(text) > 400 else ""))
                print("-" * 64)

    avg = sum(latencies) / len(latencies)
    print("\n" + "=" * 64)
    print(f"  KẾT QUẢ [{label}]")
    print(f"  Latency trung bình: {avg:.2f} s  (min {min(latencies):.2f}s / max {max(latencies):.2f}s)")
    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
