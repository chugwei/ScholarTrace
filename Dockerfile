FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE uv.lock ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 scholartrace \
    && mkdir -p /app/state \
    && chown -R scholartrace:scholartrace /app

USER scholartrace
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

ENTRYPOINT ["scholartrace", "web"]
