#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
source .env
set +a
export CATALOG_TEST_MONGO_URI="mongodb://admin:${CATALOG_MONGO_ROOT_PASSWORD}@localhost:57017/?authSource=admin"
export CATALOG_MONGO_URI="mongodb://catalog:${CATALOG_MONGO_PASSWORD}@localhost:57017/coachconnect_exercises?authSource=coachconnect_exercises"
cd exercise-service
if command -v uv >/dev/null 2>&1; then
  uv run --locked pytest "$@"
elif [[ -x ../.local/catalog-tools/bin/uv ]]; then
  ../.local/catalog-tools/bin/uv run --locked pytest "$@"
else
  echo 'Installe uv pour exécuter les tests Python.' >&2
  exit 1
fi
