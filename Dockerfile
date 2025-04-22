FROM python:3.10-slim

WORKDIR /app

# Install system dependencies and PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with ARG for including setup GUI
ARG INCLUDE_SETUP_GUI=false
COPY . .

# Remove setup GUI files if not needed
RUN if [ "$INCLUDE_SETUP_GUI" = "false" ]; then \
        echo "Excluding setup GUI files from production build" && \
        rm -f routes/setup_gui.py && \
        rm -rf templates/setup.html && \
        rm -rf static/setup-gui ; \
    else \
        echo "Including setup GUI files in build" ; \
    fi

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV HOST=0.0.0.0

# Create healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose the application port
EXPOSE ${PORT}

# Use Gunicorn for production
CMD gunicorn --bind ${HOST}:${PORT} --workers 2 --threads 4 "app:create_app()"