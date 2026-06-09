"""
Task 6 — Lexical Search Module.

Hỗ trợ 2 cơ chế (chọn qua tham số `method`):
    - "bm25"  : rank-bm25 (BM25Okapi) — mặc định.
    - "tfidf" : TF-IDF cosine, tự implement bằng numpy (cho phần bonus "lexical khác BM25").

----------------------------------------------------------------------------
BM25 vs TF-IDF — KHÁC NHAU Ở ĐÂU (giải thích cho demo):

  TF-IDF:  score = Σ tf(qi,d) · idf(qi)   (rồi chuẩn hoá cosine giữa 2 vector)
    • TF tăng TUYẾN TÍNH (hoặc log) theo số lần xuất hiện — từ lặp 10 lần "đáng giá"
      gần gấp 10 lần lặp 1 lần.
    • Không có cơ chế bão hoà, không mô hình hoá độ dài tài liệu (chỉ chuẩn hoá vector).
    • Là mô hình KHÔNG GIAN VECTOR: biểu diễn doc & query thành vector rồi đo cosine.

  BM25 (cải tiến của TF-IDF):
    • TF BÃO HOÀ qua tham số k1 → lặp lần 2,3 tăng điểm ít dần (lặp 50 lần ≈ lặp 10 lần).
    • LENGTH NORMALIZATION qua b: phạt tài liệu dài bất thường (so với avgdl).
    • Là mô hình XÁC SUẤT (probabilistic), không phải vector-space; thường nhỉnh hơn
      TF-IDF trên truy hồi văn bản thực tế.
    • score = Σ idf(qi) · tf·(k1+1) / (tf + k1·(1−b + b·|d|/avgdl)), k1=1.5, b=0.75.

Tokenize tiếng Việt: lowercase + tách token chữ/số (giữ dấu); có thể nâng cấp bằng
underthesea nếu muốn.
"""

import re

import numpy as np
from rank_bm25 import BM25Okapi

from .rag_utils import load_chunks

_bm25 = None
_corpus: list[dict] = []
_tfidf: dict | None = None  # {vocab, idf, matrix(L2-normalized), corpus}


def _tokenize(text: str) -> list[str]:
    """Lowercase + tách token chữ/số (giữ được từ có dấu tiếng Việt)."""
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def build_bm25_index(corpus: list[dict] | None = None):
    """Xây BM25 index từ corpus chunks (mặc định: load từ local store)."""
    global _bm25, _corpus
    _corpus = corpus if corpus is not None else load_chunks()
    if not _corpus:
        _bm25 = None
        return None
    tokenized = [_tokenize(doc["content"]) for doc in _corpus]
    _bm25 = BM25Okapi(tokenized)
    return _bm25


def build_tfidf_index(corpus: list[dict] | None = None):
    """Xây TF-IDF index (vocab + idf + ma trận doc đã L2-normalize) bằng numpy."""
    global _tfidf
    corpus = corpus if corpus is not None else load_chunks()
    if not corpus:
        _tfidf = None
        return None

    docs_tokens = [_tokenize(d["content"]) for d in corpus]
    n_docs = len(docs_tokens)

    # Document frequency cho từng term.
    df: dict[str, int] = {}
    for toks in docs_tokens:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    vocab = {t: i for i, t in enumerate(df)}

    # IDF làm trơn (smoothed): log((N+1)/(df+1)) + 1.
    idf = np.zeros(len(vocab), dtype=np.float32)
    for t, i in vocab.items():
        idf[i] = np.log((n_docs + 1) / (df[t] + 1)) + 1.0

    # Ma trận doc: tf log-normalized * idf, rồi L2-normalize từng hàng.
    matrix = np.zeros((n_docs, len(vocab)), dtype=np.float32)
    for r, toks in enumerate(docs_tokens):
        counts: dict[str, int] = {}
        for t in toks:
            counts[t] = counts.get(t, 0) + 1
        for t, c in counts.items():
            matrix[r, vocab[t]] = (1.0 + np.log(c)) * idf[vocab[t]]
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10

    _tfidf = {"vocab": vocab, "idf": idf, "matrix": matrix, "corpus": corpus}
    return _tfidf


def _tfidf_search(query: str, top_k: int) -> list[dict]:
    if _tfidf is None:
        build_tfidf_index()
    if _tfidf is None:
        return []

    vocab, idf, matrix, corpus = (
        _tfidf["vocab"], _tfidf["idf"], _tfidf["matrix"], _tfidf["corpus"]
    )
    q_vec = np.zeros(len(vocab), dtype=np.float32)
    counts: dict[str, int] = {}
    for t in _tokenize(query):
        if t in vocab:
            counts[t] = counts.get(t, 0) + 1
    for t, c in counts.items():
        q_vec[vocab[t]] = (1.0 + np.log(c)) * idf[vocab[t]]

    norm = np.linalg.norm(q_vec)
    if norm <= 1e-9:
        return []
    scores = matrix @ (q_vec / norm)  # cosine (matrix đã normalize)

    top_idx = np.argsort(scores)[::-1][:top_k]
    results = []
    for i in top_idx:
        if scores[i] <= 0:
            continue
        results.append(
            {
                "content": corpus[i]["content"],
                "score": float(scores[i]),
                "metadata": corpus[i].get("metadata", {}),
            }
        )
    return results


def lexical_search(query: str, top_k: int = 10, method: str = "bm25") -> list[dict]:
    """
    Tìm kiếm từ khóa.

    Args:
        method: "bm25" (mặc định) hoặc "tfidf" (cosine TF-IDF, phần bonus "khác BM25").

    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        sorted by score descending (chỉ trả về chunk có score > 0).
    """
    if method == "tfidf":
        return _tfidf_search(query, top_k)

    if _bm25 is None or not _corpus:
        build_bm25_index()
    if _bm25 is None:
        return []

    scores = _bm25.get_scores(_tokenize(query))
    top_idx = np.argsort(scores)[::-1][:top_k]

    results = []
    for i in top_idx:
        if scores[i] <= 0:
            continue
        results.append(
            {
                "content": _corpus[i]["content"],
                "score": float(scores[i]),
                "metadata": _corpus[i].get("metadata", {}),
            }
        )
    return results


if __name__ == "__main__":
    for r in lexical_search("Điều 248 tàng trữ trái phép chất ma tuý", top_k=5):
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
