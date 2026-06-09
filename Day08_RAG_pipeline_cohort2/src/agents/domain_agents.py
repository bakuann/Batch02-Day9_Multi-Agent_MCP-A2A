"""Domain agents — mỗi agent chỉ truy hồi trên MỘT kho dữ liệu.

LegalAgent → chỉ chunk metadata.type == "legal" (pháp luật ma túy).
NewsAgent  → chỉ chunk metadata.type == "news"  (tin tức nghệ sĩ liên quan).

Mỗi agent tái dùng đúng pipeline hybrid của Task 9 (semantic ∥ lexical → RRF →
rerank), nhưng LỌC ứng viên theo domain trước khi hợp nhất → kết quả chuyên biệt,
không bị lẫn nguồn của domain khác.
"""

from __future__ import annotations

from ..task5_semantic_search import semantic_search
from ..task6_lexical_search import lexical_search
from ..task7_reranking import rerank, rerank_rrf

RERANK_METHOD = "cross_encoder"


def _filter_domain(chunks: list[dict], domain: str) -> list[dict]:
    """Giữ lại các chunk thuộc đúng domain (theo metadata.type)."""
    return [c for c in chunks if c.get("metadata", {}).get("type") == domain]


def retrieve_domain(
    query: str,
    domain: str,
    top_k: int = 5,
    use_reranking: bool = True,
    use_hyde: bool = False,
    lexical_method: str = "bm25",
) -> list[dict]:
    """Hybrid retrieval (Task 9) nhưng GIỚI HẠN trong một domain.

    Lấy dư ứng viên (top_k*4) rồi lọc domain để bù phần bị loại, sau đó RRF + rerank.
    """
    # Lấy dư rồi mới lọc domain (vì index trộn 2 loại) — tránh thiếu ứng viên.
    dense = _filter_domain(semantic_search(query, top_k=top_k * 4, use_hyde=use_hyde), domain)
    sparse = _filter_domain(lexical_search(query, top_k=top_k * 4, method=lexical_method), domain)

    merged = rerank_rrf([dense, sparse], top_k=top_k * 2)
    for item in merged:
        item["source"] = "hybrid"
        item["domain"] = domain

    if use_reranking and merged:
        final = rerank(query, merged, top_k=top_k, method=RERANK_METHOD)
        for item in final:
            item.setdefault("source", "hybrid")
            item["domain"] = domain
    else:
        final = merged[:top_k]

    return final[:top_k]


class _DomainAgent:
    """Agent truy hồi cho một domain cụ thể."""

    name: str = "domain-agent"
    domain: str = ""

    def run(self, query: str, top_k: int = 5, **kwargs) -> dict:
        chunks = retrieve_domain(query, self.domain, top_k=top_k, **kwargs)
        return {
            "agent": self.name,
            "domain": self.domain,
            "chunks": chunks,
            "found": len(chunks),
        }


class LegalAgent(_DomainAgent):
    """Chuyên gia pháp luật ma túy — chỉ tra kho văn bản luật."""

    name = "legal-agent"
    domain = "legal"


class NewsAgent(_DomainAgent):
    """Chuyên gia tin tức — chỉ tra kho bài báo."""

    name = "news-agent"
    domain = "news"
