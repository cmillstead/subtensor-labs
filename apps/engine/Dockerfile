FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy application code
COPY . .

# Run as non-root user
RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE 8000

# Single worker for dev/small deployments. For production with multiple cores,
# use: gunicorn engine.main:app -w 4 -k uvicorn.workers.UvicornWorker
CMD ["uv", "run", "uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
