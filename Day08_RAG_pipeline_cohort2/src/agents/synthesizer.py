"""Synthesizer — gộp bằng chứng từ các agent rồi sinh câu trả lời có citation.

Tái dùng nguyên tầng generation của Task 10 (build_messages có phòng thủ prompt
injection + reorder chống lost-in-the-middle). Đây là "agent tổng hợp" cuối cùng.
"""

from __future__ import annotations

from ..rag_utils import CHAT_MODEL, get_client
from ..task10_generation import TEMPERATURE, TOP_P, build_messages

_NO_EVIDENCE = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def synthesize(query: str, chunks: list[dict], history: list[dict] | None = None) -> str:
    """Sinh câu trả lời (không stream) từ chunks đã gộp."""
    if not chunks:
        return _NO_EVIDENCE
    resp = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=build_messages(query, chunks, history),
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    return resp.choices[0].message.content


def synthesize_stream(query: str, chunks: list[dict], history: list[dict] | None = None):
    """Sinh câu trả lời dạng STREAM (yield từng đoạn token). Dùng cho server."""
    if not chunks:
        yield _NO_EVIDENCE
        return
    gen = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=build_messages(query, chunks, history),
        temperature=TEMPERATURE,
        top_p=TOP_P,
        stream=True,
    )
    for ev in gen:
        delta = ev.choices[0].delta.content if ev.choices else None
        if delta:
            yield delta
