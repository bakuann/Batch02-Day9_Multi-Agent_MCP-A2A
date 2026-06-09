"""
Demo backend (FastAPI) cho RAG Chatbot — phục vụ frontend tĩnh trong web/.

    GET  /            -> web/index.html (giao diện demo)
    POST /api/chat    -> stream NDJSON: {sources} rồi {token...} rồi {done}

Chạy:
    uv run uvicorn server:app --reload --port 8000
    # mở http://localhost:8000
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.rag_utils import CHAT_MODEL, get_client
from src.source_labels import friendly_label
from src.task9_retrieval_pipeline import retrieve
from src.task10_generation import TEMPERATURE, TOP_P, build_messages
from src.agents import orchestrate_retrieve

WEB_DIR = Path(__file__).parent / "web"
STD_LEGAL = Path(__file__).parent / "data" / "standardized" / "legal"
LANDING_NEWS = Path(__file__).parent / "data" / "landing" / "news"

app = FastAPI(title="RAG Pháp luật Ma túy")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    top_k: int = 5
    use_reranking: bool = True
    use_hyde: bool = False
    lexical_method: str = "bm25"  # "bm25" | "tfidf"
    multi_agent: bool = False  # True -> dùng orchestrator multi-agent (supervisor)


def _source_card(chunk: dict) -> dict:
    meta = chunk.get("metadata", {})
    source = meta.get("source", "?")
    doc_type = meta.get("type", "unknown")
    return {
        "source": source,
        "label": friendly_label(source, doc_type),
        "type": doc_type,
        "score": round(float(chunk.get("score", 0)), 3),
        "via": chunk.get("source", "hybrid"),
        "snippet": chunk["content"][:280].strip(),
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    def stream():
        # 1) Retrieve — chọn 1 trong 2 đường: multi-agent (supervisor) hoặc đơn (Task 9).
        route_info = None
        if req.multi_agent:
            chunks, route_info = orchestrate_retrieve(
                req.message,
                top_k=req.top_k,
                use_reranking=req.use_reranking,
                use_hyde=req.use_hyde,
                lexical_method=req.lexical_method,
            )
        else:
            chunks = retrieve(
                req.message,
                top_k=req.top_k,
                use_reranking=req.use_reranking,
                use_hyde=req.use_hyde,
                lexical_method=req.lexical_method,
            )
        via = chunks[0].get("source", "hybrid") if chunks else "none"
        yield json.dumps(
            {
                "type": "sources",
                "via": via,
                "mode": "multi_agent" if req.multi_agent else "single",
                "route": route_info,
                "sources": [_source_card(c) for c in chunks],
            },
            ensure_ascii=False,
        ) + "\n"

        if not chunks:
            yield json.dumps(
                {"type": "token", "text": "Tôi không thể xác minh thông tin này từ nguồn hiện có."},
                ensure_ascii=False,
            ) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return

        # 2) Generate (Task 10) — reorder + spotlighting chống injection + memory + stream.
        gen = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=build_messages(req.message, chunks, req.history),
            temperature=TEMPERATURE,
            top_p=TOP_P,
            stream=True,
        )
        for ev in gen:
            delta = ev.choices[0].delta.content if ev.choices else None
            if delta:
                yield json.dumps({"type": "token", "text": delta}, ensure_ascii=False) + "\n"

        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/api/corpus")
def corpus():
    """Danh sách tài liệu & bài báo hệ thống đang dùng (hiện trên UI)."""
    legal = [
        {"label": friendly_label(f.name, "legal"), "file": f.name}
        for f in sorted(STD_LEGAL.glob("*.md"))
    ]
    news = []
    if LANDING_NEWS.exists():
        for f in sorted(LANDING_NEWS.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            news.append(
                {
                    "title": d.get("title", f.stem),
                    "url": d.get("url", ""),
                    "date": d.get("date", ""),
                    "author": d.get("author", ""),
                }
            )
    return {"legal": legal, "news": news}


# Frontend tĩnh (đặt cuối để không che /api/*).
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
