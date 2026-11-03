# ---------------------------------------------------------------------------
# STAGE: WORKLOAD
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS workload

WORKDIR /app
COPY . .
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libpq-dev curl \
    && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt
EXPOSE 8005
CMD ["gunicorn", "-c", "gunicorn.conf.py", "--bind", "0.0.0.0:8005", "app:app"]