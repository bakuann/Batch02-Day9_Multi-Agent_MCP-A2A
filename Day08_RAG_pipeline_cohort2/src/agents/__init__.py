"""Multi-Agent (Supervisor pattern) cho RAG.

Tái tổ chức retrieval đơn thành multi-agent có điều phối:

    Supervisor (định tuyến theo domain)
        ├─ LegalAgent  (chỉ truy hồi kho LUẬT)   ─┐  chạy song song
        └─ NewsAgent   (chỉ truy hồi kho TIN TỨC) ─┘
                          │
                    Synthesizer (gộp + sinh câu trả lời có citation)

Tái dùng toàn bộ task5–task10 (semantic/lexical/RRF/rerank/generation), KHÔNG
thêm thư viện nặng — đúng triết lý "API-first" của repo.
"""

from .domain_agents import LegalAgent, NewsAgent
from .supervisor import route
from .synthesizer import synthesize, synthesize_stream
from .orchestrator import Orchestrator, orchestrate_retrieve

__all__ = [
    "LegalAgent",
    "NewsAgent",
    "route",
    "synthesize",
    "synthesize_stream",
    "Orchestrator",
    "orchestrate_retrieve",
]
