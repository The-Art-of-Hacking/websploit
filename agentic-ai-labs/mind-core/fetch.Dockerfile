# python:3.13-slim multi-arch index (linux/amd64 and linux/arm64), published 2026-10-06.
# Same digest as mind-core. The process drops to uid 10001 before any download.
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    MIND_CORE_MODEL_DIR=/models

WORKDIR /app

RUN groupadd --system --gid 10001 mindcore \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin --no-create-home mindcore \
    && mkdir -p /models \
    && chown 10001:10001 /models /app \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
    && rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.13

COPY --chown=10001:10001 model_pin.py fetch_model.py ./

# Root at start so the entrypoint can chown a root-owned named volume.
# fetch_model.py calls setuid(10001) before it opens a connection.
CMD ["python", "fetch_model.py"]
