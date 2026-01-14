FROM python:3.10-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    ffmpeg \
    aria2 \
    mediainfo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV COOKIES_FILE_PATH="youtube_cookies.txt"

CMD gunicorn app:app --bind 0.0.0.0:$PORT & python3 main.py
