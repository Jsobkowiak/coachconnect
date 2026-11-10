#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
source .env
set +a
export CATALOG_MONGO_URI="mongodb://catalog:${CATALOG_MONGO_PASSWORD}@localhost:57017/coachconnect_exercises?authSource=coachconnect_exercises"
exec exercise-service/.venv/bin/python -m exercise_catalog.cli media "$@"
