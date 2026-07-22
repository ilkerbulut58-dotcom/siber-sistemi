#!/usr/bin/env bash
# Run api-realistic-active benchmark N times for repeatability (Faz 11.5).
set -euo pipefail

ROOT="${1:-.}"
RUNS="${2:-5}"
COMPOSE_FILE="${ROOT}/docker-compose.realistic.yml"
STORAGE="${BENCHMARK_STORAGE_PATH:-/tmp/siber-benchmark-api-repeat}"

mkdir -p "${STORAGE}/reports"

docker compose -f "$COMPOSE_FILE" --profile realistic --profile realistic-runner build benchmark-runner

for i in $(seq 1 "$RUNS"); do
  echo "=== API active repeat run ${i}/${RUNS} ==="
  docker compose -f "$COMPOSE_FILE" --profile realistic --profile realistic-runner run --rm \
    -v "${STORAGE}:${STORAGE}" \
    -e "DATABASE_URL=${DATABASE_URL:?DATABASE_URL is required}" \
    -e "REDIS_URL=${REDIS_URL:?REDIS_URL is required}" \
    -e "BENCHMARK_GATE_MODE=report" \
    -e "BENCHMARK_STORAGE_PATH=${STORAGE}" \
    -e "BENCHMARK_ACTIVE_REALISTIC_ENABLED=true" \
    -e "BENCHMARK_ACTIVE_SCAN_ALLOWED=true" \
    benchmark-runner run --suite api-realistic-active --subset main
done

python "${ROOT}/scripts/summarize-determinism-runs.py" "${STORAGE}" "${RUNS}"
