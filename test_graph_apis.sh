#!/bin/bash
# Smoke script for the unified RAG API

QUESTION="đại học công nghệ và đại học quốc gia hà nội có mối quan hệ gì với nhau?"
API_URL="${API_URL:-http://localhost:8001/query}"

echo "=========================================="
echo "Testing: $QUESTION"
echo "=========================================="
echo ""

for MODE in semantic_search graph_search naive_grag hybrid; do
  echo "$MODE"
  echo "---"
  curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "{
      \"question\": \"$QUESTION\",
      \"mode\": \"$MODE\",
      \"top_k\": 5,
      \"include_evidence\": false
    }" | jq -r '.answer'
  echo ""
done

echo "=========================================="
echo "Unified API comparison complete"
echo "=========================================="
