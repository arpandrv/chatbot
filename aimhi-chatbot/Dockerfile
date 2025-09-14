FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# System deps
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 5000

# Runtime env (override in deployment)
ENV FLASK_ENV=production \
    PORT=5000

# Start with gunicorn (prod), respect PORT if provided by platform
CMD ["/bin/sh", "-lc", "exec gunicorn -w 2 -b 0.0.0.0:${PORT:-5000} aimhi-chatbot.app:app"]
