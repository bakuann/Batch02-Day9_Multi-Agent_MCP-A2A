"""Challenge 2: Conversation Memory

Thêm bộ nhớ hội thoại để agent NHỚ các câu hỏi/câu trả lời trước đó và có thể
trả lời các câu hỏi tiếp theo (follow-up) một cách mạch lạc.

Cách làm: dùng LangGraph `create_react_agent` + `MemorySaver` checkpointer.
Mỗi cuộc hội thoại có một `thread_id`; checkpointer lưu lại toàn bộ message history
theo thread đó, nên lượt sau agent vẫn "thấy" được ngữ cảnh lượt trước.

Chạy:
    uv run python exercises/challenge_2_memory.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from common.llm import get_llm


@tool
def search_legal_knowledge(query: str) -> str:
    """Tìm kiếm thông tin pháp lý cơ bản theo từ khóa."""
    kb = {
        "hợp đồng": "Tranh chấp hợp đồng dân sự: thời hiệu khởi kiện 3 năm (BLDS 2015).",
        "lao động": "Tranh chấp lao động cá nhân: thời hiệu yêu cầu Tòa án là 1 năm.",
        "thừa kế": "Tranh chấp thừa kế: 30 năm với bất động sản, 10 năm với động sản.",
    }
    for k, v in kb.items():
        if k in query.lower():
            return v
    return "Không tìm thấy thông tin; hãy nêu rõ loại tranh chấp."


SYSTEM_PROMPT = (
    "Bạn là trợ lý pháp lý. Trả lời ngắn gọn bằng tiếng Việt. "
    "Bạn NHỚ các câu hỏi trước trong cùng cuộc hội thoại và có thể tham chiếu lại. "
    "Dùng tool search_legal_knowledge khi cần tra cứu."
)


def build_agent():
    """Tạo ReAct agent có checkpointer (memory)."""
    llm = get_llm()
    # MemorySaver = bộ nhớ in-process; lưu state theo thread_id giữa các lượt invoke.
    memory = MemorySaver()
    agent = create_react_agent(
        model=llm,
        tools=[search_legal_knowledge],
        prompt=SYSTEM_PROMPT,
        checkpointer=memory,
    )
    return agent


async def ask(agent, thread_id: str, question: str) -> str:
    """Gửi 1 câu hỏi vào thread (giữ nguyên context của các lượt trước)."""
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
    )
    return result["messages"][-1].content


async def main():
    load_dotenv()
    agent = build_agent()
    thread_id = "conversation-001"

    # Hội thoại nhiều lượt — lượt 2 và 3 là follow-up, KHÔNG nhắc lại chủ đề.
    turns = [
        "Thời hiệu khởi kiện tranh chấp hợp đồng là bao lâu?",
        "Thế còn tranh chấp lao động thì sao?",          # follow-up: 'thế còn ... thì sao'
        "Trong hai loại tôi vừa hỏi, loại nào có thời hiệu ngắn hơn?",  # cần nhớ cả 2 lượt trước
    ]

    print("=" * 70)
    print("CHALLENGE 2: CONVERSATION MEMORY (multi-turn)")
    print("=" * 70)

    for i, q in enumerate(turns, 1):
        print(f"\n[Lượt {i}] 👤 {q}")
        answer = await ask(agent, thread_id, q)
        print(f"[Lượt {i}] 🤖 {answer}")

    print("\n" + "=" * 70)
    print("Nếu lượt 2 & 3 trả lời đúng mà KHÔNG cần nhắc lại chủ đề")
    print("=> memory hoạt động: agent nhớ được ngữ cảnh các lượt trước.")
    print("=" * 70)

    # Chứng minh ngược lại: thread_id KHÁC -> không có ký ức cũ.
    print("\n[Kiểm chứng] Hỏi câu follow-up trên một thread MỚI (no memory):")
    fresh = await ask(agent, "conversation-EMPTY", "Trong hai loại tôi vừa hỏi, loại nào ngắn hơn?")
    print(f"🤖 {fresh}")


if __name__ == "__main__":
    asyncio.run(main())
