"""
Task 5 — Semantic Search Module (dense retrieval).

Embed query bằng cùng model ở Task 4 (Gemini text-embedding-004), rồi tính
cosine similarity với toàn bộ chunk embeddings trong local store.
"""

import numpy as np

from .rag_utils import (
    CHAT_MODEL,
    cosine_similarity,
    embed_query,
    get_client,
    load_chunks,
    load_embeddings,
)

# HyDE: sinh "tài liệu giả định" trả lời câu hỏi, rồi embed nó thay vì embed câu hỏi.
# Lý do: câu hỏi và đoạn văn trả lời nằm ở vùng vector khác nhau; một đoạn văn giả
# (dù chưa chắc đúng) lại gần các chunk đáp án hơn -> recall ngữ nghĩa tốt hơn.
_HYDE_PROMPT = (
    "Bạn là chuyên gia pháp luật và báo chí Việt Nam về ma túy. Viết MỘT đoạn văn ngắn "
    "(3-5 câu) trả lời trực tiếp câu hỏi dưới đây, dùng văn phong và thuật ngữ giống văn "
    "bản luật / bài báo (kể cả khi không chắc chính xác tuyệt đối). Chỉ trả về đoạn văn, "
    "không rào đón.\n\nCâu hỏi: {q}"
)


def generate_hyde(query: str) -> str:
    """Sinh đoạn văn giả định (Hypothetical Document) cho query."""
    try:
        resp = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": _HYDE_PROMPT.format(q=query)}],
            temperature=0.3,
        )
        text = resp.choices[0].message.content
        return text.strip() if text else query
    except Exception:
        return query  # lỗi -> fallback dùng query gốc


def semantic_search(query: str, top_k: int = 10, use_hyde: bool = False) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa bằng vector similarity.

    Args:
        use_hyde: nếu True, embed "tài liệu giả định" (HyDE) thay vì embed câu hỏi.

    Returns:
        List of {'content': str, 'score': float (cosine), 'metadata': dict}
        sorted by score descending. Rỗng nếu chưa index (Task 4).
    """
    chunks = load_chunks()
    embeddings = load_embeddings()
    if not chunks or embeddings.shape[0] == 0:
        return []

    embed_target = generate_hyde(query) if use_hyde else query
    q_vec = embed_query(embed_target)
    scores = cosine_similarity(q_vec, embeddings)

    top_idx = np.argsort(scores)[::-1][:top_k]
    return [
        {
            "content": chunks[i]["content"],
            "score": float(scores[i]),
            "metadata": chunks[i].get("metadata", {}),
        }
        for i in top_idx
    ]


if __name__ == "__main__":
    for r in semantic_search("hình phạt cho tội tàng trữ ma tuý", top_k=5):
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
