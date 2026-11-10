#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local/catalog/media
# Also refresh the API image and its read-only asset mount.
docker compose --profile catalog --profile etl up -d --build --wait catalog-api prefect
docker compose --profile catalog --profile etl run --rm catalog-etl exercise-etl import-media "$@"
