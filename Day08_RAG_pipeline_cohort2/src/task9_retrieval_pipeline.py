"""
Task 9 — Retrieval Pipeline Hoàn Chỉnh.

    Query
      ├→ Semantic Search (Task 5) ─┐
      │                            ├→ Merge RRF → Rerank (Task 7) → Results
      ├→ Lexical Search (Task 6) ──┘
      │
      └→ Nếu kết quả hybrid yếu (rỗng hoặc best score < threshold)
            → Fallback: PageIndex Vectorless (Task 8)
"""

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search

# =============================================================================
# CONFIGURATION
# =============================================================================

SCORE_THRESHOLD = 0.3   # best score < threshold -> fallback PageIndex
DEFAULT_TOP_K = 5
RERANK_METHOD = "cross_encoder"


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
    use_hyde: bool = False,
    lexical_method: str = "bm25",
) -> list[dict]:
    """
    Retrieval pipeline hoàn chỉnh với fallback logic.

    Args:
        use_hyde: bật HyDE (Hypothetical Document Embeddings) cho nhánh semantic.
        lexical_method: "bm25" (mặc định) hoặc "tfidf" cho nhánh lexical.

    Returns:
        List of {'content', 'score', 'metadata', 'source'} với
        source ∈ {'hybrid', 'pageindex'}.
    """
    # Step 1: chạy semantic + lexical (lấy dư để merge)
    dense = semantic_search(query, top_k=top_k * 2, use_hyde=use_hyde)
    sparse = lexical_search(query, top_k=top_k * 2, method=lexical_method)

    # Step 2: merge bằng RRF
    merged = rerank_rrf([dense, sparse], top_k=top_k * 2)
    for item in merged:
        item["source"] = "hybrid"

    # Step 3: rerank cross-encoder
    if use_reranking and merged:
        final = rerank(query, merged, top_k=top_k, method=RERANK_METHOD)
        for item in final:
            item.setdefault("source", "hybrid")
    else:
        final = merged[:top_k]

    # Step 4: fallback PageIndex nếu hybrid yếu
    best_score = final[0]["score"] if final else 0.0
    if not final or best_score < score_threshold:
        print(
            f"  ⚠ Hybrid yếu (best={best_score:.3f} < {score_threshold}). "
            f"Fallback → PageIndex"
        )
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback[:top_k]
        except Exception as e:
            print(f"  ⚠ PageIndex không khả dụng ({e}); giữ kết quả hybrid.")

    return final[:top_k]


if __name__ == "__main__":
    test_queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý",
        "Nghệ sĩ nào bị bắt vì sử dụng ma tuý",
        "Luật phòng chống ma tuý 2021 quy định gì về cai nghiện",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}\n" + "-" * 60)
        for i, r in enumerate(retrieve(q, top_k=3), 1):
            print(f"  {i}. [{r['score']:.3f}] [{r['source']}] {r['content'][:80]}...")
