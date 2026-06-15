#!/usr/bin/env bash
set -euo pipefail

deadline=$((SECONDS + 180))
until curl -fsS http://localhost:8080/health/ready >/dev/null; do
  if (( SECONDS > deadline )); then
    docker compose ps
    docker compose logs --tail=120 api workflow-worker extraction-worker classification-worker
    exit 1
  fi
  sleep 2
done
