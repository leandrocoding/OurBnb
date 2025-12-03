FROM python:3.12-slim

WORKDIR /app

# Install procps for pgrep (used in k8s health checks)
RUN apt-get update && apt-get install -y --no-install-recommends procps && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv pip install --system -r pyproject.toml

# Copy source code
COPY . .

# Run celery worker
CMD ["celery", "-A", "worker", "worker", "--loglevel=info", "-Q", "high_priority,default"]
