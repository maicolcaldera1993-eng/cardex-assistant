FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FASTEMBED_CACHE_PATH=/app/.fastembed
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY web ./web
COPY samples ./samples

# download the embedding model and build the vector cache at build time, not at every start
RUN python -c "from app.core.semantic import SemanticIndex; s = SemanticIndex(); s.load(); print('semantic ready', s.ready)"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
