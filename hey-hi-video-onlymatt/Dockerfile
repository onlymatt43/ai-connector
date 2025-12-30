FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:$PYTHONPATH

WORKDIR /app

# Copy shared module from parent context
COPY shared ./shared

# Copy service requirements and install
COPY hey-hi-video-onlymatt/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY hey-hi-video-onlymatt ./hey-hi-video-onlymatt

WORKDIR /app/hey-hi-video-onlymatt

EXPOSE 10000
ENV PORT=10000

CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT}
