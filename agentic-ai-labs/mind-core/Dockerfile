# python:3.13-slim multi-arch index (linux/amd64 and linux/arm64), published 2026-10-06.
# Pinning the index digest lets Buildx select the native arch. No packages are
# installed after this pull, so the running container does not need network egress.
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

# Bare `docker run` stays on the rules engine. Compose overrides this to `auto`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    MIND_CORE_BACKEND=deterministic

WORKDIR /app

RUN groupadd --system --gid 10001 mindcore \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin --no-create-home mindcore \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
    && rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.13 \
    && chown 10001:10001 /app

COPY --chown=10001:10001 app.py rules.json ./
COPY --chown=10001:10001 mindcore ./mindcore

USER 10001:10001

EXPOSE 5030

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5030/health', timeout=2).read()"]

CMD ["python", "app.py"]
