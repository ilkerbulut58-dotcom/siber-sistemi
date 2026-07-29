FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

ARG NUCLEI_VERSION=3.3.7

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    unzip \
    fonts-dejavu-core \
    && curl -sL "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
        -o /tmp/nuclei.zip \
    && unzip -j /tmp/nuclei.zip nuclei -d /usr/local/bin \
    && chmod +x /usr/local/bin/nuclei \
    && rm /tmp/nuclei.zip \
    && rm -rf /var/lib/apt/lists/*

ENV NUCLEI_TEMPLATES=/opt/nuclei-templates

RUN mkdir -p /opt/nuclei-templates \
    && nuclei -update-templates -ud /opt/nuclei-templates \
    && chmod -R a+rX /opt/nuclei-templates

FROM base AS development

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /var/siber/mobile \
    && chown -R appuser:appuser /app /var/siber/mobile
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

ARG GIT_COMMIT=""
ARG RELEASE_TAG=""
ARG BUILD_TIMESTAMP=""
LABEL org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.version="${RELEASE_TAG}" \
      org.opencontainers.image.created="${BUILD_TIMESTAMP}"

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN sed -i 's/\r$//' scripts/celery_worker_healthcheck.sh scripts/celery_mobile_worker_healthcheck.sh \
    && chmod +x scripts/celery_worker_healthcheck.sh scripts/celery_mobile_worker_healthcheck.sh

ENV GIT_COMMIT=${GIT_COMMIT} \
    RELEASE_TAG=${RELEASE_TAG} \
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /var/siber/mobile \
    && chown -R appuser:appuser /app /var/siber/mobile
USER appuser

EXPOSE 8000

# HEALTHCHECK is defined per-service in docker-compose (api vs celery workers).

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
