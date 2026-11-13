#!/usr/bin/env bash
# VPS : sauvegarde la base sportive (données utilisateurs) dans .local/backups/, garde 14 jours.
# À lancer avant chaque déploiement et chaque nuit (cron).
set -euo pipefail
cd "$(dirname "$0")/../.."
dir=.local/backups; mkdir -p "$dir"; chmod 700 "$dir"
docker compose ps --status running --services | grep -qx training-db || { echo "training-db arrêtée : pas de sauvegarde."; exit 0; }
file="$dir/training-$(date +%Y%m%d-%H%M%S).dump"
docker compose exec -T training-db pg_dump -U training -d coachconnect_training -Fc > "$file"
chmod 600 "$file"
find "$dir" -name 'training-*.dump' -mtime +14 -delete
echo "Sauvegarde : $file ($(du -h "$file" | cut -f1))"
