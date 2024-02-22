# Use an official Python runtime as a parent image
FROM python:3.12.1-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    jq \
    apt-file \
    python3-dev build-essential \
    procps \
    libpq-dev \
    redis-server \
    && apt-file update \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt ./

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip>=23.3 grpcio \
    && pip install --no-cache-dir -r requirements.txt

# Install additional Python packages
RUN python -m spacy download en_core_web_lg \
    && python -m nltk.downloader stopwords \
    && python -m nltk.downloader punkt

# Copy the rest of the application
COPY . .

# Install Galaxy UI from swirlai/spyglass:preview
COPY --from=swirlai/spyglass:preview /usr/src/spyglass/ui/dist/spyglass/browser/. ./swirl/static/galaxy
COPY --from=swirlai/spyglass:preview /usr/src/spyglass/ui/config-swirl-demo.db.json .

# Make ports available to the world outside this container
EXPOSE 8000
