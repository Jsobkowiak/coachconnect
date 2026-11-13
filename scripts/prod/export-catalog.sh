#!/usr/bin/env bash
# PC local : exporte le catalogue (MongoDB + médias) vers .local/prod-transfer/ pour le VPS.
# Aucune donnée personnelle : la base sportive (PostgreSQL) n'est pas exportée.
set -euo pipefail
cd "$(dirname "$0")/../.."
out=.local/prod-transfer; mkdir -p "$out"; chmod 700 "$out"
stamp=$(date +%Y%m%d-%H%M%S)
docker compose exec -T catalog-mongo sh -c \
  'mongodump --quiet -u admin -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --db coachconnect_exercises --archive --gzip' \
  > "$out/catalog-$stamp.archive.gz"
tar -czf "$out/catalog-media-$stamp.tar.gz" -C .local/catalog media
ls -lh "$out"/*"$stamp"*
echo "Copie vers le VPS : scp $out/*$stamp* <utilisateur>@<vps>:<dossier-projet>/.local/prod-transfer/"
