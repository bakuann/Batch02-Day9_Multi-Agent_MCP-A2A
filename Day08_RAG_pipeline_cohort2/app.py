"""
RAG Chatbot — Pháp luật ma tuý & tin tức nghệ sĩ (bài nhóm, Yêu cầu 1).

Stack:  Streamlit → Retrieval (Task 9) → Generation Gemini (Task 10) → Display
Tính năng:
    - Chat UI có conversation memory (multi-turn, follow-up)
    - Trả lời có citation [nguồn]
    - Hiển thị source documents (score, loại, trích đoạn)

Chạy:
    uv run streamlit run app.py
"""

import streamlit as st

from src.rag_utils import CHAT_MODEL, get_client
from src.task9_retrieval_pipeline import retrieve
from src.task10_generation import TEMPERATURE, TOP_P, build_messages

st.set_page_config(page_title="RAG — Pháp luật ma tuý", page_icon="⚖️", layout="wide")


def answer_with_memory(query, history, top_k, use_reranking, use_hyde=False, lexical_method="bm25"):
    """Retrieve + generate có ngữ cảnh hội thoại (memory)."""
    chunks = retrieve(
        query, top_k=top_k, use_reranking=use_reranking,
        use_hyde=use_hyde, lexical_method=lexical_method,
    )
    if not chunks:
        return "Tôi không thể xác minh thông tin này từ nguồn hiện có.", [], "none"

    # build_messages: spotlighting + nhắc lại quy tắc (chống prompt injection) + memory.
    resp = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=build_messages(query, chunks, history),
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    return resp.choices[0].message.content, chunks, chunks[0].get("source", "hybrid")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Cấu hình")
    top_k = st.slider("Top-K chunks", 3, 10, 5)
    use_reranking = st.toggle("Dùng reranking (Jina)", value=True)
    use_hyde = st.toggle("Dùng HyDE", value=False, help="Embed tài liệu giả định thay vì câu hỏi")
    lexical_method = st.radio("Lexical search", ["bm25", "tfidf"], horizontal=True,
                              help="BM25 (xác suất, bão hoà TF) vs TF-IDF (vector-space cosine)")
    st.caption(f"Model: `{CHAT_MODEL}`")
    if st.button("🗑️ Xoá hội thoại"):
        st.session_state.messages = []
        st.rerun()

st.title("⚖️ RAG Chatbot — Pháp luật ma tuý & tin tức")
st.caption("Hỏi về luật phòng chống ma tuý, hình phạt, hoặc các vụ việc nghệ sĩ liên quan.")

# ---------------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render lịch sử
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"📚 {len(msg['sources'])} nguồn đã dùng · retrieval: {msg.get('via')}"):
                for i, s in enumerate(msg["sources"], 1):
                    meta = s.get("metadata", {})
                    st.markdown(
                        f"**{i}. {meta.get('source', '?')}** "
                        f"`{meta.get('type', '?')}` · score={s.get('score', 0):.3f}"
                    )
                    st.caption(s["content"][:300] + "…")

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
if prompt := st.chat_input("Nhập câu hỏi của bạn…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang truy hồi & trả lời…"):
            # Lịch sử (loại bỏ field phụ) để làm memory
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            answer, sources, via = answer_with_memory(
                prompt, history, top_k, use_reranking, use_hyde, lexical_method
            )
        st.markdown(answer)
        if sources:
            with st.expander(f"📚 {len(sources)} nguồn đã dùng · retrieval: {via}"):
                for i, s in enumerate(sources, 1):
                    meta = s.get("metadata", {})
                    st.markdown(
                        f"**{i}. {meta.get('source', '?')}** "
                        f"`{meta.get('type', '?')}` · score={s.get('score', 0):.3f}"
                    )
                    st.caption(s["content"][:300] + "…")

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources, "via": via}
    )
