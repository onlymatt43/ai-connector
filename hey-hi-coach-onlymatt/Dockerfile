FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:$PYTHONPATH

WORKDIR /app

# Copy shared module first
COPY ../shared ./shared

# Copy service requirements and install
COPY hey-hi-coach-onlymatt/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY hey-hi-coach-onlymatt ./hey-hi-coach-onlymatt

WORKDIR /app/hey-hi-coach-onlymatt

EXPOSE 10000
ENV PORT=10000

CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT}
