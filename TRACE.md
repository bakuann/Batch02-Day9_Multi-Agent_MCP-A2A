# Stage 5 — Trace Request Flow (A2A Multi-Agent)

> Bài tập chấm điểm (INSTRUCTOR_GUIDE.md › *Đánh Giá Sinh Viên* → "Trace request flow Stage 5: 20 điểm"):
> tìm `trace_id` trong logs, vẽ sequence diagram, đếm số hops.

Dữ liệu dưới đây trích từ **log thật** của một request chạy qua hệ phân tán (xem `logs/*.err.log`).
Câu hỏi test: *"If a company breaks a contract and avoids taxes, what are the legal and regulatory consequences?"*

---

## 1. Một trace duy nhất đi xuyên toàn hệ thống

- **trace_id:**  `09bac94c-b344-46d5-9dea-8096a3649329`
- **context_id:** `4d2295fa-d4b6-4a0c-9e45-835bc2129fc6`

Cả `trace_id` và `context_id` được **giữ nguyên** qua mọi service (trace propagation), còn
`delegation_depth` tăng dần theo mỗi hop để chống vòng lặp vô hạn (`MAX_DELEGATION_DEPTH = 3`).

| Thời điểm | Service | depth | Sự kiện (trích log) |
|---|---|---|---|
| 14:44:37 | **customer_agent** | 0 | `CustomerAgent executing ... trace=09bac94c ... depth=0` |
| 14:44:41 | customer_agent | 0 | `Customer delegate_to_legal_agent ... depth=0` → gọi Law qua A2A |
| 14:44:42 | **law_agent** | 1 | `LawAgent executing ... trace=09bac94c ... depth=1` |
| 14:44:58 | **tax_agent** | 2 | `TaxAgent executing ... trace=09bac94c ... depth=2` |
| 14:44:58 | **compliance_agent** | 2 | `ComplianceAgent executing ... trace=09bac94c ... depth=2` |

→ Tax và Compliance cùng nhận request ở **14:44:58** với **cùng depth=2** ⇒ chạy **song song** (LangGraph `Send` API).

---

## 2. Sequence diagram

```
User
 │  (1) câu hỏi
 ▼
┌──────────────────┐
│ Customer Agent   │ depth=0   :10100
│ (ReAct)          │
└───────┬──────────┘
        │ (2) discover("legal_question") → Registry :10000
        │ (3) A2A delegate ────────────────────────────► HOP 1
        ▼
┌──────────────────┐
│ Law Agent        │ depth=1   :10101
│ (StateGraph)     │
│  • analyze_law   │
│  • check_routing │
└───┬───────────┬──┘
    │ (4a)      │ (4b)   discover("tax_question") / ("compliance_question") → Registry
    │ A2A       │ A2A delegate  ──────────────────────► HOP 2 & HOP 3 (song song)
    ▼           ▼
┌─────────┐ ┌──────────────┐
│Tax Agent│ │Compliance Ag.│  depth=2   :10102 / :10103
│(ReAct)  │ │(ReAct)       │
└────┬────┘ └──────┬───────┘
     │ tax_result  │ compliance_result
     └──────┬──────┘
            ▼
   ┌──────────────────┐
   │ Law: aggregate   │  gộp law + tax + compliance → final_answer
   └────────┬─────────┘
            │ trả ngược lên Customer
            ▼
       Customer Agent → trả lời User
```

---

## 3. Trả lời câu hỏi của bài lab

**Q: Request đi qua bao nhiêu hops?**

- **3 A2A hops** (lời gọi mạng giữa các service):
  1. Customer → Law
  2. Law → Tax  *(song song)*
  3. Law → Compliance  *(song song)*
- Tính cả chiều về (kết quả đi ngược lên) thì đường đi đầy đủ là:
  `User → Customer → Law → [Tax ∥ Compliance] → Law(aggregate) → Customer → User`.
- **Delegation depth tối đa = 2** (Customer=0, Law=1, specialists=2).

**Q: Tại sao cần `trace_id`?**
Một request "fan-out" qua nhiều service/đa luồng; `trace_id` chung giúp ghép tất cả log rời rạc
thành **một dòng thời gian thống nhất** để debug (ai gọi ai, bước nào chậm/lỗi).

**Q: Vai trò Registry?**
Không hardcode URL — mỗi agent tự `register` lúc khởi động và các agent khác `discover` theo *task name*
(`legal_question`, `tax_question`, `compliance_question`) lúc runtime ⇒ dynamic discovery, dễ scale/thay thế.

---

## 4. Fault tolerance (đã có sẵn trong code)

Bài lab gợi ý "dừng Tax Agent rồi chạy lại — hệ thống có crash không?". Câu trả lời: **không crash**.
`law_agent/graph.py` bọc mỗi lời gọi specialist trong `try/except`:

```python
except Exception as exc:
    logger.exception("call_tax failed: %s", exc)
    return {"tax_result": f"[Tax analysis unavailable: {exc}]"}
```

⇒ Nếu một specialist chết, Law Agent vẫn tổng hợp phần còn lại (graceful degradation) thay vì sập toàn hệ thống.

---

## 5. Cách tái lập

```powershell
.\start_all.ps1                      # khởi động 5 service (Windows)
uv run python test_client.py         # gửi 1 câu hỏi
# Xem trace trong logs\*.err.log, lọc theo trace=<uuid>
.\stop_all.ps1
```
(Linux/macOS: `./start_all.sh`.)
```bash
# Lọc 1 trace xuyên suốt:
grep -r "trace=09bac94c" logs/
```
