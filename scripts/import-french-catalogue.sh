#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --profile catalog build catalog-api
docker compose --profile catalog run --rm --no-deps catalog-api exercise-etl import-french
docker compose --profile catalog up -d --wait catalog-api
