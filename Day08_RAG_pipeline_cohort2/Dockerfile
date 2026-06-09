# Web demo (FastAPI) — image slim, không tải model (dùng Gemini API).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Deps runtime
COPY requirements-deploy.txt .
RUN pip install -r requirements-deploy.txt

# Mã nguồn + frontend + chỉ những dữ liệu cần lúc chạy
COPY server.py ./
COPY src/ ./src/
COPY web/ ./web/
COPY data/index/ ./data/index/
COPY data/standardized/ ./data/standardized/
COPY data/landing/news/ ./data/landing/news/

# HF Spaces dùng 7860; Render/khác inject $PORT.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860}"]
