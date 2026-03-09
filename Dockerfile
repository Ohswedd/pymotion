FROM python:3.12-slim

# System dependencies for Cairo, FreeType, and FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libcairo2-dev \
        pkg-config \
        libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files and install
COPY . .
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["pymotion"]
