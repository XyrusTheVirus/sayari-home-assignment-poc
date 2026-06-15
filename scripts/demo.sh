#!/usr/bin/env bash
set -euo pipefail

require() {
  command -v "$1" >/dev/null || { echo "missing prerequisite: $1" >&2; exit 1; }
}

phase() {
  printf '\n== %s ==\n%s\n' "$1" "$2"
}

require docker
require curl
require jq

phase "1. Start services" "Build the local image, start Postgres, Temporal, MinIO, the API, and all workers."
docker compose up --build -d
./scripts/wait-for-services.sh
echo "Temporal UI: http://localhost:8088"

submit() {
  local id=$1
  local file=$2
  jq -n --arg document_id "$id" --rawfile text "$file" '{document_id:$document_id,text:$text}' \
    | curl -fsS -X POST http://localhost:8080/process -H 'Content-Type: application/json' -d @-
}

query_tokens() {
  local id=$1
  local query=$2
  curl -fsS "http://localhost:8080/documents/${id}/tokens?${query}" | jq .
}

wait_complete() {
  local id=$1
  local status
  local deadline=$((SECONDS + 180))
  while true; do
    status=$(curl -fsS "http://localhost:8080/documents/${id}/status")
    echo "$status" | jq -er . >/dev/null
    echo "$status" | jq -r '"status=\(.status) processed=\(.classification.processed_count // 0) total=\(.classification.total_tokens // 0)"' >&2
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

phase "2. Small document happy path" "Submit a short document, wait for completion, query PERSON tokens, and print stage durations."
small_id="demo-small-$(date +%s)"
submit "$small_id" test_documents/small.txt | jq .
small_status=$(wait_complete "$small_id")
curl -fsS "http://localhost:8080/documents/${small_id}/tokens?classification=PERSON" | jq .
echo "$small_status" | jq '{extraction_ms:.extraction.duration_ms, classification_ms:.classification.duration_ms}'

phase "3. Large document progress and worker recovery" "Submit a large document, watch classification progress, stop the classifier worker mid-run, and verify processing resumes."
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
  if [[ "$seen_progress" == false && "$state" == "CLASSIFYING" && "$processed" -gt 0 && "$processed" -lt "$total" ]]; then
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

phase "4. Full rerun isolation" "Complete an initial run, start a rerun with new source text, verify the old active result stays published until the rerun completes."
rerun_id="demo-rerun-$(date +%s)"
submit "$rerun_id" test_documents/small.txt >/dev/null
before=$(wait_complete "$rerun_id" | jq -r '.active_run_id')
jq -n --arg text "Elena Park joined Contoso LLC at 800 Pine Street on 2026-06-15." '{text:$text,reuse_source:false}' \
  | curl -fsS -X POST "http://localhost:8080/api/v1/documents/${rerun_id}/rerun" -H 'Content-Type: application/json' -d @- | jq .
during=$(curl -fsS "http://localhost:8080/documents/${rerun_id}/status" | jq -r '.active_run_id')
test "$before" = "$during"
after=$(wait_complete "$rerun_id" | jq -r '.active_run_id')
test "$before" != "$after"

phase "5. Concurrent document submissions" "Submit small, medium, and large documents at the same time to exercise independent workflow execution."
concurrent_suffix="$(date +%s)"
concurrent_small_id="concurrent-small-${concurrent_suffix}"
concurrent_medium_id="concurrent-medium-${concurrent_suffix}"
concurrent_large_id="concurrent-large-${concurrent_suffix}"
for pair in \
  "$concurrent_small_id test_documents/small.txt" \
  "$concurrent_medium_id test_documents/medium.txt" \
  "$concurrent_large_id test_documents/large.txt"; do
  set -- $pair
  submit "$1" "$2" >/dev/null &
done
wait
wait_complete "$concurrent_small_id" >/dev/null
wait_complete "$concurrent_medium_id" >/dev/null
wait_complete "$concurrent_large_id" >/dev/null

phase "6. Filtered token queries" "Query the completed small, medium, and large documents using classification, page, NLP type, and status filters."
echo "Small document: PERSON tokens on page 1 from PERSON NLP candidates"
query_tokens "$concurrent_small_id" "classification=PERSON&page_number=1&nlp_type=PERSON"
echo "Medium document: COMPANY tokens on page 2 from completed ORG NLP candidates"
query_tokens "$concurrent_medium_id" "classification=COMPANY&page_number=2&nlp_type=ORG&classification_status=COMPLETED"
echo "Large document: ADDRESS tokens on page 1 from completed ADDRESS NLP candidates"
query_tokens "$concurrent_large_id" "classification=ADDRESS&page_number=1&nlp_type=ADDRESS&classification_status=COMPLETED&limit=10"
