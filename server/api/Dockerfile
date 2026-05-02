FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/server/api

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY server/api /app/server/api
RUN pip install --no-cache-dir ".[server]"

EXPOSE 8000
CMD ["uvicorn", "nuclear_random_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
