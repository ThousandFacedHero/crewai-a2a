FROM python:3.12-slim AS base

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY config/ config/

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:5000/healthz').raise_for_status()"

CMD ["uv", "run", "python", "-m", "crewai_a2a.server"]
