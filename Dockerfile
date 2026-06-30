FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download the Linux yt-dlp standalone binary (bin/ is gitignored, not in build context)
RUN mkdir -p bin && \
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp \
         -o bin/yt-dlp && \
    chmod +x bin/yt-dlp

EXPOSE 3000

CMD gunicorn --workers 1 --threads 8 --timeout 30 --bind "0.0.0.0:${PORT:-3000}" slack_app:app
