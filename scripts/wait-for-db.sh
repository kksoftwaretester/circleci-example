#!/usr/bin/env bash
set -euo pipefail

HOST="${DB_HOST:-localhost}"
PORT="${DB_PORT:-5432}"
TIMEOUT="${DB_TIMEOUT:-30}"

echo "Waiting for postgres at ${HOST}:${PORT} (timeout: ${TIMEOUT}s)..."

elapsed=0
until pg_isready -h "$HOST" -p "$PORT" -q; do
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "ERROR: postgres not ready after ${TIMEOUT}s" >&2
    exit 1
  fi
  sleep 1
  elapsed=$((elapsed + 1))
done

echo "postgres is ready after ${elapsed}s"
