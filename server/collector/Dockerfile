FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/server/collector

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY server/collector /app/server/collector
RUN pip install --no-cache-dir ".[collector]"

CMD ["python", "-m", "collector.main"]
