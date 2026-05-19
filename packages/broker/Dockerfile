# hearme-broker — Python 3.11 + FastAPI + asyncpg + pynacl.
# Build context: repo root (docker-compose sets `context: .`).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libsodium is needed by pynacl's bundled bindings on some platforms; the
# `slim` image lacks it. Installing it explicitly keeps wheel install fast.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libsodium23 \
    && rm -rf /var/lib/apt/lists/*

COPY packages/broker/pyproject.toml ./pyproject.toml
COPY packages/broker/src ./src
# README is referenced by pyproject.toml; supply a minimal placeholder so
# the build doesn't fail if the file is excluded by .dockerignore.
COPY packages/broker/README.md ./README.md

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
    CMD python -c "import urllib.request,sys; \
import urllib.error; \
req=urllib.request.Request('http://localhost:8000/healthz'); \
sys.exit(0 if urllib.request.urlopen(req, timeout=2).status==200 else 1)" \
    || exit 1

CMD ["uvicorn", "hearme_broker.main:app", "--host", "0.0.0.0", "--port", "8000"]
