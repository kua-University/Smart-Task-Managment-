# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# ── Runtime config ─────────────────────────────────────────────────────────────
# Store the SQLite database in a named volume so data persists across restarts
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/tasks.db

EXPOSE 5000

# Run with Gunicorn in production; falls back to Flask dev server if not installed
CMD ["python", "app.py"]
