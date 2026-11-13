#!/usr/bin/env bash
# VPS : met à jour le code, sauvegarde, reconstruit et relance. Les volumes sont conservés.
# Usage : ./scripts/prod/deploy.sh [référence-git, ex. v0.1.0 ; défaut : origin/main]
set -euo pipefail
cd "$(dirname "$0")/../.."
grep -q '^COMPOSE_FILE=.*compose.prod.yaml' .env || { echo ".env de production absent : lancer scripts/prod/init-env.sh." >&2; exit 1; }
git fetch --tags origin
ref=${1:-origin/main}
git checkout --detach "$ref"
./scripts/prod/backup.sh
docker compose up -d --build --wait --remove-orphans
docker image prune -f >/dev/null
echo "Déployé : $(git describe --tags --always) — https://joincoachconnect.com"
