# Bài Tập Cộng Điểm — Stage 5 (A2A Multi-Agent)

> `CODELAB.md` › *Bài Tập Cộng Điểm* gồm 2 phần:
> 1. **Viết file HTML demo tương tác của các Agent** (Stage 4 / Stage 5).
> 2. Chạy full Stage 5, trả lời 2 câu hỏi: latency là bao nhiêu giây? + đề xuất & demo giảm latency.

---

## Phần 1 — HTML demo tương tác các Agent ✅

File: **[demo_stage5.html](demo_stage5.html)** — mở trực tiếp bằng trình duyệt (self-contained,
không cần server, không cần internet). Nội dung:

- Sơ đồ 5 service (Registry / Customer / Law / Tax / Compliance) với cổng & delegation depth.
- Nút **"Chạy demo"** animate **một request thật** (replay theo log + `trace_id` thật): gói tin
  chạy dọc các cạnh, node sáng lên theo thứ tự xử lý, Tax ∥ Compliance chạy song song.
- Panel **nhật ký tương tác** hiển thị từng bước (discover → A2A delegate → fan-out → aggregate).
- Hiển thị **kết quả tổng hợp** và **biểu đồ so sánh latency** (baseline vs optimized) của Phần 2.

---

## Phần 2 — Latency: đo + tối ưu

Mô hình dùng: `google/gemini-2.5-flash` (OpenRouter), `max_tokens=2048`.
Câu hỏi test: *"If a company breaks a contract and avoids taxes, what are the legal and regulatory consequences?"*

---

## Câu 1 — Latency hiện tại (BASELINE)

Đo bằng `test_client_timed.py` (bấm giờ quanh `client.send_message`).

| Lần chạy | Latency |
|---|---|
| Run 1 | **58.72 s** |
| Run 2 | **50.45 s** |
| **Trung bình** | **≈ 54.6 s** |

### Vì sao chậm? — Phân tích critical path

Một câu hỏi đi qua chuỗi LLM call **tuần tự**:

```
Customer (ReAct: quyết định delegate)         →  1 LLM
  Law: analyze_law                            →  1 LLM
  Law: check_routing (LLM chỉ để chọn route)  →  1 LLM   ← lãng phí
  Law: [tax_agent || compliance_agent]        →  ~1–2 LLM mỗi nhánh (song song)
  Law: aggregate                              →  1 LLM
Customer (ReAct: trình bày lại kết quả)       →  1 LLM
```

Hai điểm nghẽn chính nằm ở **Law Agent**:
- **`check_routing` tốn nguyên 1 LLM call** chỉ để trả về `{needs_tax, needs_compliance}`.
- **`analyze_law` chạy TUẦN TỰ trước** tax/compliance — dù tax/compliance chỉ cần `question`, *không* cần `law_analysis`. Tức là phần phân tích pháp lý và các specialist lẽ ra có thể chạy song song lại đang nối tiếp.

Bằng chứng từ log (`logs/law_agent.err.log`, 1 request baseline):
```
14:44:44  POST openrouter        # analyze_law
14:44:58  POST openrouter        # check_routing  (+14s)
14:44:58  GET  /discover/tax_question        # mãi giờ mới gọi specialist
14:44:58  GET  /discover/compliance_question
14:45:16  POST openrouter        # aggregate
```
→ specialist chỉ được dispatch ở **t+16s**, sau khi 2 LLM call (analyze + routing) đã xong.

---

## Câu 2 — Phương án giảm latency + Demo

### Phương án

Tối ưu topology của **Law Agent** (file `law_agent/graph.py`, bật bằng `LAW_OPTIMIZED=1`):

1. **Bỏ LLM call `check_routing`** → thay bằng **routing theo keyword** (`route_from_start`), tốn ~0 giây thay vì 1 round-trip LLM.
2. **Fan-out SONG SONG ngay từ `START`**: `analyze_law`, `call_tax`, `call_compliance` chạy đồng thời (vì độc lập dữ liệu), rồi mới `aggregate`.

```
# Trước:  analyze_law → check_routing → [tax || compliance] → aggregate   (3 LLM call tuần tự ở law)
# Sau:    START → [analyze_law || tax || compliance] → aggregate          (2 LLM call ở law)
```

Critical path của Law Agent rút từ
`analyze + routing + max(tax,compliance) + aggregate`
xuống còn
`max(analyze, tax, compliance) + aggregate`.

### Demo — đo lại sau khi apply

Chạy lại đúng câu hỏi với `LAW_OPTIMIZED=1`:

| Cấu hình | Latency (run sạch) |
|---|---|
| BASELINE | 58.72 s / 50.45 s → **~54.6 s** |
| **OPTIMIZED** | **43.07 s** |

> ✅ **Giảm ~11.5 s (~21%)** trên một câu hỏi.
> (Run thứ 2 của bản optimized trả về rỗng sau 2.8s do tài khoản OpenRouter free **hết credit** — lỗi `402 Payment Required`, *không* phải do tối ưu; xem `logs/*.opt.err.log`.)

Bằng chứng từ log (`logs/law_agent.opt.err.log`, 1 request optimized):
```
14:49:03.2  LawAgent executing
14:49:03.9  GET /discover/tax_question          # specialist dispatch NGAY (t+0.7s)
14:49:03.9  GET /discover/compliance_question
14:49:04.6  POST openrouter   # analyze_law chạy SONG SONG với specialist
14:49:26    POST openrouter   # aggregate
```
→ Chỉ còn **2 LLM call** phía law (mất hẳn call routing), và specialist khởi động ở **t+0.7s** thay vì t+16s.

### Cách tái lập (Windows)

```powershell
# 1) Baseline
.\start_all.ps1
$env:TIMED_LABEL="BASELINE"; uv run python test_client_timed.py
.\stop_all.ps1

# 2) Optimized
$env:LAW_OPTIMIZED="1"; .\start_all.ps1
$env:TIMED_LABEL="OPTIMIZED"; uv run python test_client_timed.py
.\stop_all.ps1
```
(Linux/macOS: `export LAW_OPTIMIZED=1` rồi `./start_all.sh`.)

---

## Các hướng giảm latency thêm (ngoài phạm vi đã demo)

- **Streaming** (`capabilities.streaming=True`): hiện chữ ngay khi token đầu tiên về → giảm *perceived latency* mạnh.
- **Giảm `max_tokens`** cho các bước trung gian (analyze/specialist) vì chỉ `aggregate` cần dài.
- **Bỏ bớt 1 hop ReAct ở Customer Agent**: với câu hỏi pháp lý rõ ràng, delegate thẳng thay vì để LLM quyết định 2 lần (vào + ra).
- **Prompt/response caching** cho các câu hỏi lặp lại.
- **Model nhỏ hơn cho bước routing/specialist**, model mạnh chỉ cho `aggregate`.
