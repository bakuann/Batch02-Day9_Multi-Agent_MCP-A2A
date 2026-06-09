"""Challenge 3: Custom Tool gọi API THẬT

Tạo một tool tra cứu thuật ngữ pháp lý từ một API online thật:
Wikipedia REST API (miễn phí, KHÔNG cần API key).

    GET https://{lang}.wikipedia.org/api/rest_v1/page/summary/{term}

LLM sẽ tự quyết định gọi tool, tool gọi HTTP thật, rồi LLM tổng hợp câu trả lời.

Chạy:
    uv run python exercises/challenge_3_custom_tool.py
"""

import asyncio
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from common.llm import get_llm


@tool
def lookup_legal_term(term: str, lang: str = "vi") -> str:
    """Tra cứu định nghĩa một thuật ngữ pháp lý từ Wikipedia (API online thật).

    Args:
        term: Thuật ngữ cần tra cứu, ví dụ "Thời hiệu", "Hợp đồng", "GDPR".
        lang: Mã ngôn ngữ Wikipedia ("vi" tiếng Việt, "en" tiếng Anh).
    """
    slug = urllib.parse.quote(term.strip().replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{slug}"
    try:
        resp = httpx.get(url, timeout=10.0, headers={"User-Agent": "legal-codelab/1.0"})
        if resp.status_code == 404:
            # Thử fallback sang tiếng Anh nếu tiếng Việt không có
            if lang != "en":
                return lookup_legal_term.func(term, lang="en")
            return f"Không tìm thấy bài viết Wikipedia cho '{term}'."
        resp.raise_for_status()
        data = resp.json()
        extract = data.get("extract", "").strip()
        title = data.get("title", term)
        if not extract:
            return f"Không có nội dung tóm tắt cho '{term}'."
        return f"[Wikipedia:{title}] {extract}"
    except Exception as exc:
        return f"Lỗi khi gọi Wikipedia API: {exc}"


async def main():
    load_dotenv()
    llm = get_llm()

    tools = [lookup_legal_term]
    llm_with_tools = llm.bind_tools(tools)

    question = "GDPR là gì? Hãy tra cứu và giải thích ngắn gọn cho người không chuyên."

    messages = [
        SystemMessage(content=(
            "Bạn là chuyên gia pháp lý. Khi cần định nghĩa thuật ngữ, hãy dùng tool "
            "lookup_legal_term để tra cứu từ Wikipedia rồi diễn giải lại dễ hiểu."
        )),
        HumanMessage(content=question),
    ]

    print("=" * 70)
    print("CHALLENGE 3: CUSTOM TOOL gọi API thật (Wikipedia)")
    print("=" * 70)
    print(f"\nCâu hỏi: {question}\n")

    response = await llm_with_tools.ainvoke(messages)
    messages.append(response)

    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"🔧 Gọi tool: {tc['name']}  args={tc['args']}")
            if tc["name"] == "lookup_legal_term":
                tool_result = lookup_legal_term.invoke(tc["args"])
                print(f"   ↳ API trả về: {tool_result[:160]}...\n")
                messages.append(ToolMessage(content=tool_result, tool_call_id=tc["id"]))

        final = await llm_with_tools.ainvoke(messages)
        print(f"✅ Kết quả:\n{final.content}")
    else:
        print(f"✅ Kết quả (không gọi tool):\n{response.content}")


if __name__ == "__main__":
    asyncio.run(main())
