#!/usr/bin/env bash
set -euo pipefail

require() {
  command -v "$1" >/dev/null || { echo "missing prerequisite: $1" >&2; exit 1; }
}

require docker
require curl
require jq

docker compose up --build -d
./scripts/wait-for-services.sh
echo "Temporal UI: http://localhost:8088"

submit() {
  local id=$1
  local file=$2
  jq -n --arg document_id "$id" --rawfile text "$file" '{document_id:$document_id,text:$text}' \
    | curl -fsS -X POST http://localhost:8080/process -H 'Content-Type: application/json' -d @-
}

wait_complete() {
  local id=$1
  local deadline=$((SECONDS + 180))
  while true; do
    status=$(curl -fsS "http://localhost:8080/documents/${id}/status")
    echo "$status" | jq -r '"status=\(.status) processed=\(.classification.processed_count // 0) total=\(.classification.total_tokens // 0)"'
    if [[ $(echo "$status" | jq -r .status) == "COMPLETED" ]]; then
      echo "$status"
      return 0
    fi
    if (( SECONDS > deadline )); then
      echo "timeout waiting for $id" >&2
      exit 1
    fi
    sleep 2
  done
}

small_id="demo-small-$(date +%s)"
submit "$small_id" test_documents/small.txt | jq .
small_status=$(wait_complete "$small_id")
curl -fsS "http://localhost:8080/documents/${small_id}/tokens?classification=PERSON" | jq .
echo "$small_status" | jq '{extraction_ms:.extraction.duration_ms, classification_ms:.classification.duration_ms}'

large_id="demo-large-$(date +%s)"
submit "$large_id" test_documents/large.txt | jq .
seen_progress=false
deadline=$((SECONDS + 180))
while true; do
  status=$(curl -fsS "http://localhost:8080/documents/${large_id}/status")
  processed=$(echo "$status" | jq -r '.classification.processed_count // 0')
  total=$(echo "$status" | jq -r '.classification.total_tokens // 0')
  state=$(echo "$status" | jq -r '.status')
  echo "status=$state processed=$processed total=$total"
  if [[ "$state" == "CLASSIFYING" && "$processed" -gt 0 && "$processed" -lt "$total" ]]; then
    seen_progress=true
    docker compose stop classification-worker
    persisted=$(curl -fsS "http://localhost:8080/documents/${large_id}/status" | jq -r '.classification.processed_count')
    test "$persisted" -ge "$processed"
    docker compose start classification-worker
  fi
  if [[ "$state" == "COMPLETED" ]]; then
    break
  fi
  if (( SECONDS > deadline )); then
    echo "timeout waiting for large document" >&2
    exit 1
  fi
  sleep 2
done
test "$seen_progress" = true

rerun_id="demo-rerun-$(date +%s)"
submit "$rerun_id" test_documents/small.txt >/dev/null
before=$(wait_complete "$rerun_id" | jq -r '.active_run_id')
jq -n --arg text "Elena Park joined Contoso LLC at 800 Pine Street on 2026-06-15." '{text:$text,reuse_source:false}' \
  | curl -fsS -X POST "http://localhost:8080/api/v1/documents/${rerun_id}/rerun" -H 'Content-Type: application/json' -d @- | jq .
during=$(curl -fsS "http://localhost:8080/documents/${rerun_id}/status" | jq -r '.active_run_id')
test "$before" = "$during"
after=$(wait_complete "$rerun_id" | jq -r '.active_run_id')
test "$before" != "$after"

for pair in "concurrent-small test_documents/small.txt" "concurrent-medium test_documents/medium.txt" "concurrent-large test_documents/large.txt"; do
  set -- $pair
  submit "$1-$(date +%s)" "$2" >/dev/null &
done
wait
curl -fsS "http://localhost:8080/documents/${small_id}/tokens?classification=PERSON&page_number=1&nlp_type=PERSON" | jq .
