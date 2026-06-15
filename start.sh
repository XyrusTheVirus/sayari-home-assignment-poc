#!/usr/bin/env bash
set -euo pipefail

docker compose up --build -d
./scripts/wait-for-services.sh
printf 'API: http://localhost:8080\n'
printf 'Temporal UI: http://localhost:8088\n'
printf 'MinIO UI: http://localhost:9001\n'
