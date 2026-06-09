"""Shared LLM factory for all agents.

Mặc định dùng OpenRouter (OpenAI-compatible). Nếu OpenRouter trả lỗi hết credit
(402 Payment Required) hoặc rate limit (429), tự động FALLBACK sang Google AI Studio
(Gemini API trực tiếp — free tier riêng, không tốn credit OpenRouter).

Cấu hình fallback qua biến môi trường:
    GEMINI_API_KEY          (hoặc GOOGLE_API_KEY) — API key của Google AI Studio
    GEMINI_FALLBACK_MODEL   — mặc định "gemini-2.5-flash"

Nếu KHÔNG đặt GEMINI_API_KEY thì get_llm() trả về ChatOpenAI bình thường (không fallback),
nên mọi thứ vẫn hoạt động như cũ.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr

logger = logging.getLogger(__name__)

# Số lần thử lại khi chính fallback (Gemini) gặp lỗi tạm thời (503/429/500)
_FALLBACK_RETRIES = 3
_FALLBACK_BACKOFF = 2.0  # giây, tăng dần

# Endpoint OpenAI-compatible của Google AI Studio (Gemini)
GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _should_fallback(exc: Exception) -> bool:
    """Quyết định có nên chuyển sang fallback không (hết credit / rate limit / kết nối)."""
    status = getattr(exc, "status_code", None)
    if status in (402, 429, 500, 502, 503):
        return True
    text = str(exc).lower()
    return any(s in text for s in (
        "payment required", "more credits", "insufficient", "quota", "rate limit", "402",
    ))


class FallbackChatOpenAI(ChatOpenAI):
    """ChatOpenAI có một model dự phòng; tự chuyển sang fallback khi gặp lỗi credit/limit.

    Vì kế thừa ChatOpenAI nên tương thích hoàn toàn với `.bind_tools()` và
    `create_react_agent(...)` — fallback hoạt động trong suốt với mọi call site.
    """

    # Private attr: không tham gia serialize/validate của pydantic
    _fallback: Optional[ChatOpenAI] = PrivateAttr(default=None)

    def set_fallback(self, fallback: Optional[ChatOpenAI]) -> "FallbackChatOpenAI":
        self._fallback = fallback
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        try:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as exc:  # noqa: BLE001
            if self._fallback is None or not _should_fallback(exc):
                raise
            logger.warning("Primary LLM lỗi (%s) → fallback sang Gemini trực tiếp", exc)
            last = exc
            for attempt in range(1, _FALLBACK_RETRIES + 1):
                try:
                    return self._fallback._generate(
                        messages, stop=stop, run_manager=run_manager, **kwargs
                    )
                except Exception as fexc:  # noqa: BLE001
                    last = fexc
                    if attempt < _FALLBACK_RETRIES and _should_fallback(fexc):
                        time.sleep(_FALLBACK_BACKOFF * attempt)
                        continue
                    raise last

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        try:
            return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as exc:  # noqa: BLE001
            if self._fallback is None or not _should_fallback(exc):
                raise
            logger.warning("Primary LLM lỗi (%s) → fallback sang Gemini trực tiếp", exc)
            last = exc
            for attempt in range(1, _FALLBACK_RETRIES + 1):
                try:
                    return await self._fallback._agenerate(
                        messages, stop=stop, run_manager=run_manager, **kwargs
                    )
                except Exception as fexc:  # noqa: BLE001
                    last = fexc
                    if attempt < _FALLBACK_RETRIES and _should_fallback(fexc):
                        await asyncio.sleep(_FALLBACK_BACKOFF * attempt)
                        continue
                    raise last


def _build_gemini_fallback(max_tokens: int) -> Optional[ChatOpenAI]:
    """Tạo client Gemini trực tiếp (Google AI Studio) nếu có API key."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None
    model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
    return ChatOpenAI(
        model=model,
        openai_api_key=key,
        openai_api_base=GEMINI_OPENAI_BASE,
        max_tokens=max_tokens,
    )


def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI client (OpenRouter) có fallback Gemini nếu được cấu hình."""
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))
    fallback = _build_gemini_fallback(max_tokens)

    primary = FallbackChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        # Giới hạn output để tiết kiệm credit (mặc định model xin tới ~65k tokens)
        max_tokens=max_tokens,
    )
    primary.set_fallback(fallback)
    if fallback is not None:
        logger.info("LLM fallback Gemini đã bật (model=%s)", fallback.model_name)
    return primary
