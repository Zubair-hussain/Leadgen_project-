# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# Set environment variables for better Python performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Install system dependencies in a single layer for better caching
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r django && useradd -r -g django django

# Set work directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt ./

# Install Python dependencies using the pip bundled with the base image
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy project files with proper ownership
COPY --chown=django:django . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media && \
    chown -R django:django /app/logs /app/staticfiles /app/media

# Create a health check script
RUN echo '#!/bin/bash\npython manage.py check --deploy' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python manage.py check --deploy || exit 1

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "leadgen.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
