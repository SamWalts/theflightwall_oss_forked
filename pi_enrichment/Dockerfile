FROM python:3.12-slim

WORKDIR /app

COPY pi_enrichment/server.py pi_enrichment/faa_pipeline.py ./
COPY pi_enrichment/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV FAA_DB_PATH=/data/faa_registry.sqlite3 \
    FAA_CSV_PATH=/data/faa_registry.csv \
    FAA_META_PATH=/data/faa_registry_meta.json \
    FLIGHTWALL_PI_HOST=0.0.0.0 \
    FLIGHTWALL_PI_PORT=8080 \
    RUN_FAA_SYNC_ON_START=true

EXPOSE 8080
VOLUME ["/data"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
