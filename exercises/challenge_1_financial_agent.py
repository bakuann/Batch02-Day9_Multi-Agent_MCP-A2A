"""Challenge 1: Thêm Financial Agent vào Multi-Agent System

Mở rộng hệ thống multi-agent (Exercise 4) với một agent chuyên phân tích
THIỆT HẠI TÀI CHÍNH. Agent này chạy SONG SONG cùng tax / compliance / privacy
thông qua LangGraph Send API.

Chạy:
    uv run python exercises/challenge_1_financial_agent.py
"""

import asyncio
import os
import sys
from typing import Annotated, TypedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from common.llm import get_llm


def _last_wins(left: str | None, right: str | None) -> str:
    """Reducer: giá trị mới ghi đè giá trị cũ (cho ghi song song)."""
    return right if right is not None else (left or "")


class State(TypedDict):
    question: str
    law_analysis: Annotated[str, _last_wins]
    tax_analysis: Annotated[str, _last_wins]
    compliance_analysis: Annotated[str, _last_wins]
    privacy_analysis: Annotated[str, _last_wins]
    financial_analysis: Annotated[str, _last_wins]  # <-- field mới cho financial agent
    final_response: str


def law_agent(state: State) -> dict:
    """Agent phân tích pháp lý tổng quát (lead attorney)."""
    llm = get_llm()
    prompt = f"""Bạn là chuyên gia pháp lý. Phân tích câu hỏi sau:

{state['question']}

Tập trung vào: hợp đồng, trách nhiệm dân sự, quyền và nghĩa vụ pháp lý.
Giữ phần trả lời dưới 200 từ."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"law_analysis": response.content}


def check_routing(state: State) -> list[Send]:
    """Quyết định gọi agents nào dựa trên nội dung câu hỏi (path function)."""
    q = state["question"].lower()
    tasks: list[Send] = []

    if any(kw in q for kw in ["tax", "irs", "thuế"]):
        tasks.append(Send("tax_agent", state))

    if any(kw in q for kw in ["compliance", "sec", "regulation", "tuân thủ"]):
        tasks.append(Send("compliance_agent", state))

    if any(kw in q for kw in ["data", "privacy", "gdpr", "dữ liệu", "rò rỉ"]):
        tasks.append(Send("privacy_agent", state))

    # Routing cho financial_agent: bất cứ khi nào có yếu tố tiền bạc / thiệt hại
    if any(kw in q for kw in [
        "financial", "money", "damage", "loss", "cost", "revenue", "fine", "penalty",
        "tài chính", "tiền", "thiệt hại", "tổn thất", "chi phí", "doanh thu", "phạt", "bồi thường",
    ]):
        tasks.append(Send("financial_agent", state))

    return tasks if tasks else [Send("aggregate_results", state)]


def tax_agent(state: State) -> dict:
    """Agent chuyên về thuế."""
    llm = get_llm()
    prompt = f"""Bạn là chuyên gia thuế. Phân tích khía cạnh thuế trong câu hỏi:

Câu hỏi: {state['question']}
Phân tích pháp lý: {state.get('law_analysis', 'N/A')}

Tập trung: IRS, tax evasion, penalties, FBAR, FATCA. Dưới 150 từ."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"tax_analysis": response.content}


def compliance_agent(state: State) -> dict:
    """Agent chuyên về compliance."""
    llm = get_llm()
    prompt = f"""Bạn là chuyên gia compliance. Phân tích khía cạnh tuân thủ:

Câu hỏi: {state['question']}
Phân tích pháp lý: {state.get('law_analysis', 'N/A')}

Tập trung: SEC, SOX, FCPA, AML, regulatory violations. Dưới 150 từ."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"compliance_analysis": response.content}


def privacy_agent(state: State) -> dict:
    """Agent chuyên về bảo vệ dữ liệu cá nhân và GDPR."""
    llm = get_llm()
    prompt = f"""Bạn là chuyên gia bảo vệ dữ liệu. Phân tích khía cạnh quyền riêng tư:

Câu hỏi: {state['question']}
Phân tích pháp lý: {state.get('law_analysis', 'N/A')}

Tập trung: GDPR, data protection, data breach, nghĩa vụ thông báo, mức phạt. Dưới 150 từ."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"privacy_analysis": response.content}


def financial_agent(state: State) -> dict:
    """Agent chuyên phân tích THIỆT HẠI TÀI CHÍNH.

    Đây là agent mới của Challenge 1: ước lượng tác động tài chính,
    các đầu mục thiệt hại, và rủi ro về dòng tiền / chi phí khắc phục.
    """
    llm = get_llm()
    prompt = f"""Bạn là chuyên gia phân tích tài chính & định giá thiệt hại (forensic accounting).
Phân tích KHÍA CẠNH TÀI CHÍNH của tình huống:

Câu hỏi: {state['question']}
Phân tích pháp lý: {state.get('law_analysis', 'N/A')}

Hãy nêu cụ thể:
- Các đầu mục thiệt hại tài chính có thể phát sinh (trực tiếp & gián tiếp)
- Ước lượng mức độ / khoảng giá trị (định tính nếu thiếu số liệu)
- Chi phí khắc phục và rủi ro dòng tiền
- Ảnh hưởng tới định giá doanh nghiệp / báo cáo tài chính
Dưới 180 từ."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"financial_analysis": response.content}


def aggregate_results(state: State) -> dict:
    """Tổng hợp kết quả từ tất cả agents thành báo cáo cuối."""
    llm = get_llm()

    sections = []
    if state.get("law_analysis"):
        sections.append(f"📋 PHÂN TÍCH PHÁP LÝ:\n{state['law_analysis']}")
    if state.get("tax_analysis"):
        sections.append(f"💰 PHÂN TÍCH THUẾ:\n{state['tax_analysis']}")
    if state.get("compliance_analysis"):
        sections.append(f"✅ PHÂN TÍCH TUÂN THỦ:\n{state['compliance_analysis']}")
    if state.get("privacy_analysis"):
        sections.append(f"🔒 PHÂN TÍCH BẢO VỆ DỮ LIỆU:\n{state['privacy_analysis']}")
    if state.get("financial_analysis"):
        sections.append(f"📊 PHÂN TÍCH THIỆT HẠI TÀI CHÍNH:\n{state['financial_analysis']}")

    combined = "\n\n".join(sections)

    prompt = f"""Tổng hợp các phân tích sau thành một báo cáo pháp lý - tài chính hoàn chỉnh:

{combined}

Câu hỏi gốc: {state['question']}

Hãy tạo báo cáo ngắn gọn, có cấu trúc rõ ràng, kèm ước lượng tổng rủi ro tài chính."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"final_response": response.content}


def build_graph():
    """Xây dựng multi-agent graph có financial_agent."""
    graph = StateGraph(State)

    graph.add_node("law_agent", law_agent)
    graph.add_node("tax_agent", tax_agent)
    graph.add_node("compliance_agent", compliance_agent)
    graph.add_node("privacy_agent", privacy_agent)
    graph.add_node("financial_agent", financial_agent)
    graph.add_node("aggregate_results", aggregate_results)

    graph.add_edge(START, "law_agent")
    graph.add_conditional_edges(
        "law_agent",
        check_routing,
        ["tax_agent", "compliance_agent", "privacy_agent", "financial_agent", "aggregate_results"],
    )
    graph.add_edge("tax_agent", "aggregate_results")
    graph.add_edge("compliance_agent", "aggregate_results")
    graph.add_edge("privacy_agent", "aggregate_results")
    graph.add_edge("financial_agent", "aggregate_results")
    graph.add_edge("aggregate_results", END)

    return graph.compile()


async def main():
    load_dotenv()

    question = (
        "Công ty bị rò rỉ dữ liệu khách hàng và vi phạm hợp đồng bảo mật. "
        "Hậu quả pháp lý, thuế và thiệt hại tài chính ước tính là gì?"
    )

    print("=" * 70)
    print("CHALLENGE 1: MULTI-AGENT + FINANCIAL AGENT")
    print("=" * 70)
    print(f"\nCâu hỏi: {question}\n")
    print("Đang xử lý qua các agents (chạy song song)...\n")

    graph = build_graph()
    result = await graph.ainvoke({
        "question": question,
        "law_analysis": "",
        "tax_analysis": "",
        "compliance_analysis": "",
        "privacy_analysis": "",
        "financial_analysis": "",
        "final_response": "",
    })

    print("\n" + "=" * 70)
    print("KẾT QUẢ CUỐI CÙNG")
    print("=" * 70)
    print(result["final_response"])
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
