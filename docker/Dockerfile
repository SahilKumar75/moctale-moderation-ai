FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies into a virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir pip==24.0
RUN pip install --no-cache-dir -r requirements.txt

COPY moctale_moderation/ moctale_moderation/
RUN pip install --no-cache-dir -e .

# Runtime image
FROM python:3.11-slim

RUN useradd -m appuser

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code and config
COPY moctale_moderation/ moctale_moderation/
COPY config/ config/

# Make sure ChromaDB directory is writable by appuser
RUN mkdir -p .chroma_db && chown -R appuser:appuser .chroma_db
RUN mkdir -p logs && chown -R appuser:appuser logs

USER appuser

EXPOSE 8000

ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "moctale_moderation.service:app", "--host", "0.0.0.0", "--port", "8000"]
