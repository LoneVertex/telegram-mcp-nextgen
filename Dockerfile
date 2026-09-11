FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY pyproject.toml requirements.txt README.md ./
COPY telegram_mcp ./telegram_mcp
COPY main.py sanitize.py session_string_generator.py ./
RUN python -m pip install --upgrade pip && \
    python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    TELEGRAM_MCP_TIER=core \
    TELEGRAM_SEND_ENABLED=false \
    TELEGRAM_DESTRUCTIVE_ENABLED=false \
    TELEGRAM_DATA_DIR=/var/lib/telegram-mcp \
    TELEGRAM_MCP_ALLOW_INSTALLED=1
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels && \
    useradd --create-home --uid 10001 --shell /usr/sbin/nologin telegram && \
    mkdir -p /var/lib/telegram-mcp && \
    chown -R telegram:telegram /app /var/lib/telegram-mcp
COPY --chown=telegram:telegram .env.example ./
USER telegram
VOLUME ["/var/lib/telegram-mcp"]
ENTRYPOINT ["telegram-mcp"]
