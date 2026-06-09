"""Orchestrator — điều phối toàn bộ luồng multi-agent.

    1. Supervisor định tuyến câu hỏi → chọn LegalAgent / NewsAgent / cả hai.
    2. Các agent được chọn chạy SONG SONG (ThreadPoolExecutor — đều là I/O API).
    3. Gộp (interleave theo rank để giữ đại diện cả 2 domain), cắt còn top_k.
    4. Synthesizer sinh câu trả lời có citation.

Hàm `orchestrate_retrieve()` tách riêng phần truy hồi để server stream phần sinh.
Lớp `Orchestrator` cung cấp `run()` end-to-end (không stream) cho CLI/eval.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .domain_agents import LegalAgent, NewsAgent
from .supervisor import route
from .synthesizer import synthesize

DEFAULT_TOP_K = 5


def _merge(results: list[dict], top_k: int) -> list[dict]:
    """Interleave chunks của các agent theo rank để cả 2 domain đều có mặt."""
    lists = [r["chunks"] for r in results if r.get("chunks")]
    merged: list[dict] = []
    depth = max((len(l) for l in lists), default=0)
    for rank in range(depth):
        for l in lists:
            if rank < len(l):
                merged.append(l[rank])
    return merged[:top_k]


def orchestrate_retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    use_reranking: bool = True,
    use_hyde: bool = False,
    lexical_method: str = "bm25",
    use_llm_router: bool = True,
) -> tuple[list[dict], dict]:
    """Supervisor → domain agents (song song) → gộp. Trả (chunks, info)."""
    decision = route(query, use_llm=use_llm_router)

    agents = []
    if decision.get("legal"):
        agents.append(LegalAgent())
    if decision.get("news"):
        agents.append(NewsAgent())

    # Mỗi agent lấy đủ top_k để phần gộp có lựa chọn; gộp xong mới cắt.
    def _run(agent):
        return agent.run(
            query,
            top_k=top_k,
            use_reranking=use_reranking,
            use_hyde=use_hyde,
            lexical_method=lexical_method,
        )

    with ThreadPoolExecutor(max_workers=max(1, len(agents))) as pool:
        results = list(pool.map(_run, agents))

    chunks = _merge(results, top_k)
    info = {
        "route_via": decision.get("via"),
        "agents": [r["agent"] for r in results],
        "per_agent_found": {r["agent"]: r["found"] for r in results},
        "domains": [r["domain"] for r in results],
    }
    return chunks, info


class Orchestrator:
    """Điều phối end-to-end (không stream) — tiện cho CLI / eval."""

    def run(
        self,
        query: str,
        history: list[dict] | None = None,
        top_k: int = DEFAULT_TOP_K,
        **kwargs,
    ) -> dict:
        chunks, info = orchestrate_retrieve(query, top_k=top_k, **kwargs)
        answer = synthesize(query, chunks, history)
        return {
            "answer": answer,
            "sources": chunks,
            "route": info,
            "retrieval_source": chunks[0].get("source", "none") if chunks else "none",
        }


if __name__ == "__main__":
    orch = Orchestrator()
    test_queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý là gì?",          # legal
        "Nghệ sĩ nào bị bắt vì sử dụng ma tuý?",                            # news
        "Luật xử lý nghệ sĩ vi phạm ma tuý thế nào và có vụ nào nổi bật?",  # both
    ]
    for q in test_queries:
        print(f"\n{'='*70}\nQ: {q}")
        res = orch.run(q, top_k=4)
        print(f"Route: {res['route']}")
        print(f"A: {res['answer'][:300]}")
        print(f"[{len(res['sources'])} chunks]")
