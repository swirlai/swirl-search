FROM python:3.12.8-slim-bookworm

# Update, upgrade and install packages in a single RUN to reduce layers
RUN apt-get update && apt-get install -y \
    apt-file \
    build-essential \
    jq \
    libpq-dev \
    procps \
    python3-dev \
    redis-server \
&& apt-file update \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

# Copy application files (see .dockerignore for list of exclusions)
COPY . /app
COPY ./db.sqlite3.dist /app/db.sqlite3
COPY ./.env.docker /app/.env
COPY ./download-nltk-resources.sh /app/

WORKDIR /app

# Optimize pip and Python installations
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade grpcio

# Swirl install requirements
RUN python -m spacy download en_core_web_lg && \
     ./download-nltk-resources.sh

# Install the Galaxy UI
COPY --from=swirlai/spyglass:preview /usr/src/spyglass/ui/dist/spyglass/browser/. /app/swirl/static/galaxy
COPY --from=swirlai/spyglass:preview /usr/src/spyglass/ui/config-swirl-demo.db.json /app/

EXPOSE 8000
