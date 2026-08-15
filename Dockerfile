FROM node:20-alpine AS frontend
WORKDIR /web
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /web/dist ./static

ENV PYTHONUNBUFFERED=1
ENV UPLOAD_DIR=/data/uploads
ENV STATIC_DIR=/app/static
ENV DATABASE_URL=sqlite:////data/specground.db

EXPOSE 8000
CMD ["sh", "-c", "mkdir -p /data/uploads && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
