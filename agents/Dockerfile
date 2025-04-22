FROM python:3.9-slim

WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY ./agents/requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY ./agents /app/agents
COPY ./utils /app/utils
COPY ./.env.example /app/.env.example

# Create log directories
RUN mkdir -p /app/logs/agent_sessions /app/logs/agent_feedback /app/logs/token_usage

# Set up environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default to disabling network access to Claude for safety
ENV CLAUDE_DISABLE_INTERNET=true
# Default allowed domains if internet is enabled
ENV CLAUDE_ALLOWED_DOMAINS="localhost,127.0.0.1"

# Default entry point runs the help
ENTRYPOINT ["python", "/app/agents/test_runner.py"]
CMD ["--help"]