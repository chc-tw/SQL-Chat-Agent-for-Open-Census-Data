# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY backend/app/ app/

# Copy dataset CSV files needed to build the ChromaDB index
COPY Dataset/FEATURE_OPTION_TABLE/ /Dataset/FEATURE_OPTION_TABLE/

# Build ChromaDB vector index from CSV files (OPENAI_API_KEY injected as BuildKit secret)
# Dummy Snowflake/Anthropic vars satisfy pydantic validation at import time; only OPENAI_API_KEY is used.
RUN --mount=type=secret,id=openai_key \
    OPENAI_API_KEY=$(cat /run/secrets/openai_key) \
    SNOWFLAKE_ACCOUNT=x SNOWFLAKE_USER=x SNOWFLAKE_PASSWORD=x \
    SNOWFLAKE_WAREHOUSE=x SNOWFLAKE_DATABASE=x SNOWFLAKE_SCHEMA=x \
    ANTHROPIC_API_KEY=x \
    uv run python -m app.utils.index_metadata && \
    rm -rf /Dataset

# Expose port
EXPOSE 8080

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
