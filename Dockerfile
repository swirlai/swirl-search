FROM python:3.13.12-slim-trixie

# Build profile (TECH_DESIGN_swirl_for_backstage.md section 3.8).
#   full      - the default image, unchanged: en_core_web_lg, every extra
#   backstage - the SWIRL for Backstage image: one small spaCy model, Presidio
#               pointed at that same model, Redis started inside the container
#               by docker/backstage/entrypoint.sh
# Build with: docker build --build-arg SWIRL_PROFILE=backstage .
ARG SWIRL_PROFILE=full
ENV SWIRL_PROFILE=${SWIRL_PROFILE}

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

# Near the top or just before WORKDIR
ENV BLIS_ARCH=generic

WORKDIR /app

# Optimize pip and Python installations; install spaCy version matching requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    SPACY_VERSION=$(grep -E '^[sS]pacy(==|>=)' requirements.txt | head -1 | sed -E 's/^[sS]pacy(==|>=)//') && \
    if [ -n "$SPACY_VERSION" ]; then \
      echo "Found spaCy version $SPACY_VERSION in requirements.txt"; \
      pip install --no-cache-dir --only-binary :all: spacy==$SPACY_VERSION || \
      pip install --no-cache-dir spacy==$SPACY_VERSION; \
    else \
      echo "No pinned spaCy version found in requirements.txt, installing latest spaCy wheel"; \
      pip install --no-cache-dir --only-binary :all: spacy || \
      pip install --no-cache-dir spacy; \
    fi && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade grpcio

# Swirl install requirements.
#
# The backstage profile installs en_core_web_sm instead of en_core_web_lg and
# repoints Presidio's default NLP configuration at it, because
# swirl/processors/remove_pii.py builds an AnalyzerEngine at import time and
# Presidio's stock conf names en_core_web_lg, which would then be missing.
# SWIRL_SPACY_MODEL_EN makes swirl/spacy.py use the same model.
RUN if [ "$SWIRL_PROFILE" = "backstage" ]; then \
      python -m spacy download en_core_web_sm && \
      PRESIDIO_CONF="$(python -c 'import os, presidio_analyzer; print(os.path.dirname(presidio_analyzer.__file__))')/conf/default.yaml" && \
      sed -i 's/en_core_web_lg/en_core_web_sm/' "$PRESIDIO_CONF" && \
      echo "backstage profile: spaCy en_core_web_sm, Presidio repointed in $PRESIDIO_CONF"; \
    else \
      python -m spacy download en_core_web_lg; \
    fi && \
    ./download-nltk-resources.sh

# The backstage profile ships its own environment defaults and runs Redis,
# Django and Celery in one container against a /data volume.
RUN if [ "$SWIRL_PROFILE" = "backstage" ]; then \
      cp /app/.env.backstage.dist /app/.env && \
      chmod +x /app/docker/backstage/entrypoint.sh; \
    fi

# Install the Galaxy UI
COPY --from=swirlai/spyglass:preview /usr/src/spyglass/ui/dist/spyglass/browser/. /app/swirl/static/galaxy
COPY --from=swirlai/spyglass:preview /usr/src/spyglass/ui/config-swirl-demo.db.json /app/

EXPOSE 8000

# The health endpoint is AllowAny and returns 503 until Redis, the Celery
# worker and the Tantivy reader are all up (TECH_DESIGN section 3.7).
HEALTHCHECK --interval=5s --timeout=5s --start-period=10s --retries=18 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/swirl/sapi/health/backstage/', timeout=4).status == 200 else 1)"

# The default image is always started with an explicit command (see
# docker-compose.yaml), which overrides this. The backstage image relies on it.
CMD ["/app/docker/backstage/entrypoint.sh"]
