"""Supervisor — định tuyến câu hỏi tới (các) domain agent phù hợp.

Dùng LLM (Gemini) làm router trả về JSON {"legal": bool, "news": bool}.
Có fallback keyword khi: thiếu API key, LLM lỗi, hoặc parse JSON thất bại.
Nếu không xác định được domain nào → chọn CẢ HAI (an toàn, không bỏ sót).
"""

from __future__ import annotations

import json

from ..rag_utils import CHAT_MODEL, get_client

_ROUTER_SYSTEM = (
    "Bạn là bộ định tuyến của hệ thống RAG đa tác tử. Dựa vào câu hỏi, quyết định "
    "cần hỏi chuyên gia nào.\n"
    'Chỉ trả về JSON hợp lệ, KHÔNG markdown, KHÔNG giải thích:\n'
    '{"legal": <true|false>, "news": <true|false>}\n\n'
    'legal = true  → liên quan pháp luật ma túy: điều luật, hình phạt, quy định, cai nghiện...\n'
    'news  = true  → liên quan tin tức/sự việc: nghệ sĩ, người nổi tiếng, vụ bắt giữ, scandal...\n'
    "Câu hỏi vừa hỏi luật vừa hỏi tin tức thì cả hai = true."
)

_LEGAL_KW = [
    "luật", "điều", "khoản", "nghị định", "hình phạt", "phạt", "tội", "tàng trữ",
    "mua bán", "vận chuyển", "cai nghiện", "quy định", "bộ luật", "hình sự", "pháp luật",
]
_NEWS_KW = [
    "nghệ sĩ", "ca sĩ", "diễn viên", "người nổi tiếng", "sao", "scandal", "bị bắt",
    "vụ", "tin tức", "báo", "showbiz", "idol", "rapper",
]


def _keyword_route(query: str) -> dict:
    q = query.lower()
    legal = any(k in q for k in _LEGAL_KW)
    news = any(k in q for k in _NEWS_KW)
    if not legal and not news:
        legal = news = True  # không rõ → hỏi cả hai
    return {"legal": legal, "news": news}


def route(query: str, use_llm: bool = True) -> dict:
    """Trả về {'legal': bool, 'news': bool, 'via': 'llm'|'keyword'}."""
    if not use_llm:
        return {**_keyword_route(query), "via": "keyword"}

    try:
        resp = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": _ROUTER_SYSTEM},
                {"role": "user", "content": query},
            ],
            temperature=0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        parsed = json.loads(raw)
        legal = bool(parsed.get("legal", False))
        news = bool(parsed.get("news", False))
        if not legal and not news:  # router phân vân → cả hai
            legal = news = True
        return {"legal": legal, "news": news, "via": "llm"}
    except Exception:
        # Bất kỳ lỗi nào (no key / quota / JSON) → fallback keyword.
        return {**_keyword_route(query), "via": "keyword"}
