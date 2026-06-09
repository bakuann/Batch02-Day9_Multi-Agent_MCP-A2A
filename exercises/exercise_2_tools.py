"""Bài Tập 2: Thêm Tools và Knowledge Base

Hoàn thành các TODO để thêm tool và knowledge base entry mới.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from common.llm import get_llm

# Knowledge base
LEGAL_KNOWLEDGE = [
    {
        "id": "ucc_breach",
        "keywords": ["breach", "contract", "remedies", "damages", "ucc"],
        "text": (
            "Under the Uniform Commercial Code (UCC) Article 2, remedies for breach of contract "
            "include: (1) expectation damages; (2) consequential damages; (3) specific performance; "
            "(4) cover damages. Statute of limitations is typically 4 years (UCC § 2-725)."
        ),
    },
    # Thêm entry về luật lao động Việt Nam
    {
        "id": "labor_law",
        "keywords": ["lao động", "sa thải", "hợp đồng lao động", "nghỉ việc", "trợ cấp"],
        "text": (
            "Theo Bộ luật Lao động 2019 (Việt Nam): người sử dụng lao động chỉ được "
            "đơn phương chấm dứt hợp đồng lao động trong các trường hợp luật định và phải "
            "báo trước (ít nhất 30 ngày với HĐ xác định thời hạn, 45 ngày với HĐ không xác "
            "định thời hạn). Sa thải trái pháp luật phải nhận lại người lao động và bồi "
            "thường ít nhất 2 tháng tiền lương. Người lao động làm việc thường xuyên từ đủ "
            "12 tháng trở lên được trợ cấp thôi việc nửa tháng lương cho mỗi năm làm việc."
        ),
    },
]


@tool
def search_legal_knowledge(query: str) -> str:
    """Tìm kiếm trong knowledge base pháp lý."""
    query_lower = query.lower()
    for entry in LEGAL_KNOWLEDGE:
        if any(kw in query_lower for kw in entry["keywords"]):
            return f"[{entry['id']}] {entry['text']}"
    return "Không tìm thấy thông tin liên quan."


# Tool check_statute_of_limitations
@tool
def check_statute_of_limitations(case_type: str) -> str:
    """Kiểm tra thời hiệu khởi kiện theo loại vụ việc (case_type)."""
    limitations = {
        "contract": "Hợp đồng (UCC § 2-725): thời hiệu khởi kiện là 4 năm kể từ khi vi phạm.",
        "hợp đồng": "Tranh chấp hợp đồng dân sự (BLDS Việt Nam): thời hiệu khởi kiện là 3 năm.",
        "tort": "Bồi thường thiệt hại ngoài hợp đồng: thời hiệu khởi kiện thường là 3 năm.",
        "lao động": "Tranh chấp lao động cá nhân: thời hiệu yêu cầu Tòa án giải quyết là 1 năm.",
        "thừa kế": "Tranh chấp về thừa kế: thời hiệu là 30 năm với bất động sản, 10 năm với động sản.",
    }
    key = case_type.lower().strip()
    for k, v in limitations.items():
        if k in key:
            return v
    return (
        f"Không có dữ liệu thời hiệu cụ thể cho loại vụ việc '{case_type}'. "
        "Thời hiệu khởi kiện mặc định cho tranh chấp dân sự thường là 3 năm."
    )


async def main():
    load_dotenv()
    llm = get_llm()
    
    # Thêm tool mới vào danh sách
    tools = [search_legal_knowledge, check_statute_of_limitations]
    llm_with_tools = llm.bind_tools(tools)
    
    question = "Thời hiệu khởi kiện vụ vi phạm hợp đồng là bao lâu?"
    
    messages = [
        SystemMessage(content="Bạn là chuyên gia pháp lý. Sử dụng tools để tra cứu thông tin."),
        HumanMessage(content=question),
    ]
    
    print(f"Câu hỏi: {question}\n")
    
    # First LLM call - decide which tools to use
    response = await llm_with_tools.ainvoke(messages)
    messages.append(response)
    
    # Execute tools if requested
    if response.tool_calls:
        for tool_call in response.tool_calls:
            print(f"🔧 Gọi tool: {tool_call['name']}")
            tool_result = None
            
            if tool_call["name"] == "search_legal_knowledge":
                tool_result = search_legal_knowledge.invoke(tool_call["args"])
            elif tool_call["name"] == "check_statute_of_limitations":
                tool_result = check_statute_of_limitations.invoke(tool_call["args"])
            
            if tool_result:
                messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call["id"]))
        
        # Second LLM call - synthesize final answer
        final_response = await llm_with_tools.ainvoke(messages)
        print(f"\n✅ Kết quả:\n{final_response.content}")
    else:
        print(f"\n✅ Kết quả:\n{response.content}")


if __name__ == "__main__":
    asyncio.run(main())
