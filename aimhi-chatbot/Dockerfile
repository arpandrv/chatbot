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

# Copy and install requirements (monorepo-safe)
COPY aimhi-chatbot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code (only the subdirectory)
COPY aimhi-chatbot/ .

# Expose port
EXPOSE 5000

# Runtime env (override in deployment)
ENV FLASK_ENV=production \
    PORT=5000

# Start with gunicorn (prod), respect PORT and WEB_CONCURRENCY
# - Workers are controlled via WEB_CONCURRENCY (default 2)
# - Additional flags can be passed via GUNICORN_CMD_ARGS env var on the platform
CMD ["/bin/sh", "-lc", "python check_env.py && exec gunicorn -w ${WEB_CONCURRENCY:-2} -b 0.0.0.0:${PORT:-5000} app:app"]
