# ARGent Docker image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code first (needed for install)
COPY pyproject.toml README.md alembic.ini ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY alembic/ ./alembic/

# Install Python dependencies
RUN pip install .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "argent.main:app", "--host", "0.0.0.0", "--port", "8000"]
