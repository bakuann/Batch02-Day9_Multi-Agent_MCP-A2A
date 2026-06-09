# Bài Tập Thực Hành

Thư mục này chứa các bài tập thực hành cho codelab A2A Multi-Agent.

## Danh Sách Bài Tập

### Exercise 2: Tools và Knowledge Base
**File:** `exercise_2_tools.py`  
**Thời gian:** 10 phút  
**Mục tiêu:** Học cách thêm tools và knowledge base vào LLM

**Nhiệm vụ:**
1. Thêm entry về luật lao động vào `LEGAL_KNOWLEDGE`
2. Tạo tool `check_statute_of_limitations` để kiểm tra thời hiệu khởi kiện
3. Test với câu hỏi về thời hiệu

**Chạy:**
```bash
uv run python exercises/exercise_2_tools.py
```

---

### Exercise 4: Multi-Agent với Privacy Agent
**File:** `exercise_4_multiagent.py`  
**Thời gian:** 15 phút  
**Mục tiêu:** Mở rộng multi-agent system với agent mới

**Nhiệm vụ:**
1. Implement `privacy_agent` function
2. Thêm conditional routing cho privacy agent
3. Thêm privacy_agent vào graph
4. Test với câu hỏi về data breach

**Chạy:**
```bash
uv run python exercises/exercise_4_multiagent.py
```

---

## Đáp Án

Đáp án chi tiết có trong file `SOLUTIONS.md`. 

**⚠️ Lưu ý:** Hãy cố gắng tự làm trước khi xem đáp án!

---

## Hướng Dẫn Làm Bài

### 1. Đọc TODO Comments
Mỗi file có các comment `# TODO:` chỉ ra chỗ cần điền code.

### 2. Tìm Gợi Ý
Các comment `# Gợi ý:` cho biết hướng làm.

### 3. Tham Khảo Stages
Code trong `stages/*` là examples tốt để tham khảo.

### 4. Test Thường Xuyên
Sau mỗi thay đổi, chạy lại để kiểm tra.

### 5. Debug
Nếu lỗi:
- Đọc error message cẩn thận
- Check syntax (dấu ngoặc, indentation)
- Thêm `print()` để xem giá trị biến
- So sánh với code trong stages

---

## Bài Tập Nâng Cao (Optional) — ĐÃ HOÀN THÀNH ✅

Tất cả challenge đã được implement thành file chạy được:

### Challenge 1: Financial Agent — `challenge_1_financial_agent.py`
Thêm `financial_agent` (phân tích thiệt hại tài chính) vào multi-agent system,
chạy SONG SONG cùng tax / compliance / privacy qua `Send` API.
```bash
uv run python exercises/challenge_1_financial_agent.py
```

### Challenge 2: Conversation Memory — `challenge_2_memory.py`
Dùng `MemorySaver` + `thread_id` để agent NHỚ các lượt hỏi trước (multi-turn,
trả lời được câu follow-up). Có kiểm chứng thread mới = không có ký ức.
```bash
uv run python exercises/challenge_2_memory.py
```

### Challenge 3: Custom Tool gọi API thật — `challenge_3_custom_tool.py`
Tool `lookup_legal_term` gọi **Wikipedia REST API** (online, không cần key) để
tra cứu thuật ngữ pháp lý; LLM tự quyết định gọi tool.
```bash
uv run python exercises/challenge_3_custom_tool.py
```

### Challenge 4: Error Handling — `challenge_4_error_handling.py`
Decorator `with_retry` (exponential backoff) + fallback + try/except ngoài cùng,
minh hoạ bằng tool flaky (lỗi 2 lần rồi thành công) và tool luôn lỗi.
```bash
uv run python exercises/challenge_4_error_handling.py
```

> ⚙️ Lưu ý Windows: chạy với UTF-8 để in tiếng Việt:
> `$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"` trước khi `uv run ...`

---

## Bài Tập Cộng Điểm (Stage 5 Latency) — ĐÃ HOÀN THÀNH ✅

Xem báo cáo đầy đủ tại **[../BONUS.md](../BONUS.md)**: đo latency baseline (~54.6s),
đề xuất tối ưu (bỏ LLM routing + fan-out song song trong Law Agent) và demo giảm
còn ~43s (≈ -21%). Công cụ: `test_client_timed.py`, `start_all.ps1`, `stop_all.ps1`.

---

## Câu Hỏi Thường Gặp

**Q: Làm sao biết code đúng chưa?**  
A: Chạy file và xem output. Nếu không có error và có kết quả hợp lý là OK.

**Q: Tool không được gọi?**  
A: Check xem đã thêm vào `tools` list và `.bind_tools()` chưa.

**Q: Agent không chạy song song?**  
A: Đảm bảo dùng `Send()` API và các agents không phụ thuộc lẫn nhau.

**Q: Import error?**  
A: Chạy `uv sync` để cài đặt dependencies.

---

## Hỗ Trợ

Nếu gặp khó khăn:
1. Đọc lại phần lý thuyết trong `CODELAB.md`
2. Xem `QUICK_REFERENCE.md` cho syntax
3. Hỏi bạn bè hoặc giảng viên
4. Check `SOLUTIONS.md` (last resort!)

**Chúc bạn làm bài tốt! 💪**
