#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --profile catalog --profile etl run --rm catalog-etl exercise-etl import "$@"
