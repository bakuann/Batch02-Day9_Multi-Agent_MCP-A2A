# Deploy demo lên online

Web demo (`server.py` + `web/`) đã được đóng gói Docker, image **slim** (không torch).
Index (`data/index/`) đã commit sẵn nên không cần build lại khi deploy.

## Bí mật cần khai báo (env vars / secrets)
| Biến | Bắt buộc | Dùng cho |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | embedding + generation |
| `JINA_API_KEY` | tùy chọn | reranking (không có thì tự fallback) |
| `PAGEINDEX_API_KEY` | tùy chọn | fallback vectorless |

> Không commit `.env`. Khai báo key trong dashboard của nền tảng.

---

## Cách 1 — Hugging Face Spaces (Docker SDK)
1. Tạo Space mới: **SDK = Docker**, Hardware = CPU basic (free).
2. Push toàn bộ repo lên Space (hoặc kết nối GitHub). Đảm bảo có: `Dockerfile`,
   `requirements-deploy.txt`, `server.py`, `src/`, `web/`, `data/index/`,
   `data/standardized/`, `data/landing/news/`.
3. Đặt README của Space có frontmatter Docker — dùng mẫu `deploy/README-huggingface.md`
   (đổi tên thành `README.md` ở gốc Space, đã set `app_port: 7860`).
4. **Settings → Variables and secrets** → thêm `GEMINI_API_KEY` (và Jina/PageIndex nếu có).
5. Space tự build Dockerfile và chạy. Mở URL Space để dùng.

## Cách 2 — Render.com (Docker, có sẵn `render.yaml`)
1. Push repo lên GitHub.
2. Render Dashboard → **New → Blueprint** → chọn repo (tự đọc `render.yaml`).
3. Nhập secret `GEMINI_API_KEY` (Jina/PageIndex nếu có) → **Apply**.
4. Render build & deploy; app lắng nghe `$PORT` tự động.

## Chạy thử Docker ở máy (tùy chọn)
```bash
docker build -t rag-druglaw .
docker run -p 7860:7860 -e GEMINI_API_KEY=... rag-druglaw
# mở http://localhost:7860
```

## Lưu ý
- Index đã build sẵn cho corpus hiện tại. Nếu đổi tài liệu, chạy lại
  `task3` + `task4` rồi commit `data/index/` mới.
- Free tier có thể "ngủ" khi không dùng — lần truy cập đầu hơi chậm.
