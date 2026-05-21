# ==========================================
# Phase 1: Build & Dependency compilation
# ==========================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install compilation essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to local wheels directory
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Phase 2: High-efficiency production runtime
# ==========================================
FROM python:3.11-slim as runner

WORKDIR /app

# Install runtime database clients (e.g. Postgres client lib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application files
COPY app /app/app
COPY templates /app/templates
COPY static /app/static
COPY run.py /app/
COPY Procfile /app/

# Environment defaults
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

EXPOSE 10000

# Run with Gunicorn on production
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "run:app"]
