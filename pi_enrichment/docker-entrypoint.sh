#!/usr/bin/env sh
set -eu

if [ "${RUN_FAA_SYNC_ON_START:-true}" = "true" ]; then
  python /app/faa_pipeline.py
fi

exec python /app/server.py --host "${FLIGHTWALL_PI_HOST:-0.0.0.0}" --port "${FLIGHTWALL_PI_PORT:-8080}"
