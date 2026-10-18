#!/usr/bin/env bash
set -euo pipefail

OUTPUT="frontend/openapi.json"
TEMPORARY="${OUTPUT}.tmp"
TYPES_OUTPUT="frontend/app/types/api.generated.ts"
TYPES_TEMPORARY="${TYPES_OUTPUT}.tmp"

docker compose exec -T backend python -c \
  "import json, urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://localhost:8000/openapi.json')), ensure_ascii=False, indent=2))" \
  >"${TEMPORARY}"

mv "${TEMPORARY}" "${OUTPUT}"
echo "Esquema OpenAPI exportado a ${OUTPUT}."

docker compose exec -T frontend \
  pnpm exec openapi-typescript openapi.json \
  >"${TYPES_TEMPORARY}"

mv "${TYPES_TEMPORARY}" "${TYPES_OUTPUT}"
echo "Tipos TypeScript generados en ${TYPES_OUTPUT}."
