FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/Ohswedd/pymotion"
LABEL org.opencontainers.image.description="PyMotion — code-first video generation for Python"
LABEL org.opencontainers.image.licenses="PyMotion Source Available License 1.0"

# System dependencies for Cairo, FreeType, HarfBuzz, and FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libcairo2-dev \
        pkg-config \
        libfreetype6-dev \
        libharfbuzz-dev \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY pymotion/ pymotion/

RUN pip install --no-cache-dir .

ENTRYPOINT ["pymotion"]
