# python:3.13-slim multi-arch index (linux/amd64 and linux/arm64), published 2026-10-06.
# Same digest mind-core pins. Buildx selects the native arch from this index.
# No packages are installed after this pull.
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    MIND_CORE_URL=http://mind-core:5030 \
    TOKEN_FAMINE_MIND_CORE_TIMEOUT_SECONDS=2 \
    TOKEN_FAMINE_REQUEST_TIMEOUT_SECONDS=2 \
    TOKEN_FAMINE_PORT=5036

WORKDIR /app

RUN groupadd --system --gid 10007 famine \
    && useradd --system --uid 10007 --gid 10007 --home-dir /nonexistent --shell /usr/sbin/nologin --no-create-home famine \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
    && rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.13 \
    && chown 10007:10007 /app

COPY --chown=10007:10007 app.py ./

USER 10007:10007

EXPOSE 5036

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5036/health', timeout=2).read()"]

CMD ["python", "app.py"]
