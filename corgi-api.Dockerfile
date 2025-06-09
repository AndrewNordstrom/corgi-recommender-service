# Multi-stage build for Corgi API
# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt
RUN pip install --user --no-cache-dir gunicorn

# Stage 2: Final image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 corgi && \
    mkdir -p /app/logs /app/data && \
    chown -R corgi:corgi /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=corgi:corgi /root/.local /home/corgi/.local

# Copy application code
COPY --chown=corgi:corgi . .

# Switch to non-root user
USER corgi

# Add local bin to PATH
ENV PATH=/home/corgi/.local/bin:$PATH

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"] 