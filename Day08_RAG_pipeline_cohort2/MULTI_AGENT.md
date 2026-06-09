# Multi-Agent (Supervisor) cho RAG

Tổ chức lại phần **truy hồi đơn** (`task9.retrieve()` — tìm trộn cả 2 kho) thành
**multi-agent có điều phối** theo mẫu *supervisor / orchestrator*.

> Bản truy hồi đơn **vẫn được giữ nguyên** — multi-agent là đường chạy song song,
> bật/tắt bằng cờ `multi_agent`, để so sánh trước/sau.

## Kiến trúc

```
Câu hỏi
   │
   ▼
Supervisor (src/agents/supervisor.py)        ← LLM router, fallback keyword
   │  quyết định domain: legal? news?
   ├───────────────┬──────────────────┐
   ▼               ▼                   (chạy SONG SONG)
LegalAgent      NewsAgent              (src/agents/domain_agents.py)
type=legal      type=news             ← mỗi agent hybrid (semantic∥lexical→RRF→rerank)
   │               │                     nhưng LỌC ứng viên theo domain
   └───────┬───────┘
           ▼
   Gộp (interleave theo rank, cắt top_k)   (src/agents/orchestrator.py)
           ▼
   Synthesizer (src/agents/synthesizer.py) ← build_messages (Task 10) + Gemini → citation
           ▼
       Câu trả lời
```

**Tái dùng 100% tầng cũ:** Task 5 (semantic), Task 6 (lexical), Task 7 (RRF/rerank),
Task 10 (build_messages + chống prompt injection + reorder). Không thêm thư viện nặng.

## Vì sao tách theo domain?

Index trộn 2 loại tài liệu (`metadata.type ∈ {legal, news}`). Truy hồi đơn dễ bị một
domain "lấn át". Tách Legal/News giúp **mỗi domain được truy hồi & rerank riêng**, rồi
mới gộp → bằng chứng cân đối hơn cho câu hỏi liên domain ("nghệ sĩ X vi phạm luật gì").

## Cách dùng

### 1) API (server.py) — thêm cờ `multi_agent`
```bash
uv sync --extra group
uv run uvicorn server:app --port 8000
```
```jsonc
POST /api/chat
{ "message": "Nghệ sĩ nào bị bắt vì ma túy và luật xử lý ra sao?",
  "multi_agent": true }
```
Sự kiện `sources` trả thêm `"mode": "multi_agent"` và `"route"` (agent nào đã chạy).
Bỏ cờ (hoặc `false`) → chạy như cũ.

### 2) CLI / code
```python
from src.agents import Orchestrator
res = Orchestrator().run("Hình phạt tội tàng trữ ma túy?", top_k=4)
print(res["route"])    # {'route_via': 'llm', 'agents': ['legal-agent'], ...}
print(res["answer"])   # câu trả lời có citation
```
Hoặc chạy demo sẵn:
```bash
uv run python -m src.agents.orchestrator
```

## Yêu cầu để chạy thật
- `GEMINI_API_KEY` trong `.env` (đã có). Model sinh: `GEMINI_CHAT_MODEL` (mặc định
  `gemini-2.5-flash-lite` — nhẹ & rẻ).
- Đã build index: `uv run python -m src.task4_chunking_indexing`.
