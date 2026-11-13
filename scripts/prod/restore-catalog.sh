#!/usr/bin/env bash
# VPS : restaure le catalogue exporté par export-catalog.sh.
# Usage : ./scripts/prod/restore-catalog.sh .local/prod-transfer/catalog-<date>.archive.gz .local/prod-transfer/catalog-media-<date>.tar.gz
set -euo pipefail
cd "$(dirname "$0")/../.."
[[ $# -eq 2 && -f $1 && -f $2 ]] || { echo "Usage : $0 <archive-mongo.gz> <medias.tar.gz>" >&2; exit 2; }
docker compose up -d --wait catalog-mongo
docker compose exec -T catalog-mongo sh -c \
  'mongorestore --quiet -u admin -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --nsInclude "coachconnect_exercises.*" --drop --archive --gzip' \
  < "$1"
mkdir -p .local/catalog
tar -xzf "$2" -C .local/catalog
echo "Catalogue restauré."
