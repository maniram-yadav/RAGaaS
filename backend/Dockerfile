# RAGaaS backend image.
#
# STORY-002 scope: a build-only image validated in CI (`docker build`), not
# yet pushed to a registry or wired into docker-compose (that's STORY-008).
# Runtime-only dependencies are installed (requirements.txt); dev/test tools
# (ruff, mypy, pytest, testcontainers) stay out of the image on purpose.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
