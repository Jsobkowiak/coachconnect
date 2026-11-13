#!/usr/bin/env bash
# VPS : crée le .env de production (secrets neufs, jamais ceux du PC).
# Usage : ./scripts/prod/init-env.sh <reseau-traefik> <certresolver> [entrypoint]
set -euo pipefail
cd "$(dirname "$0")/../.."
[[ $# -ge 2 ]] || { echo "Usage : $0 <reseau-traefik> <certresolver> [entrypoint=websecure]" >&2; exit 2; }
[[ -e .env ]] && { echo ".env existe déjà : rien n'est écrasé." >&2; exit 1; }
docker network inspect "$1" >/dev/null || { echo "Réseau Docker $1 introuvable." >&2; exit 1; }
umask 077
secret() { python3 -c 'import secrets;print(secrets.token_hex(24))'; }
cat > .env <<ENV
COMPOSE_FILE=compose.yaml:infrastructure/docker/compose.prod.yaml
COMPOSE_PROFILES=catalog,training
TRAEFIK_NETWORK=$1
TRAEFIK_CERTRESOLVER=$2
TRAEFIK_ENTRYPOINT=${3:-websecure}
CATALOG_MONGO_ROOT_PASSWORD=$(secret)
CATALOG_MONGO_PASSWORD=$(secret)
TRAINING_DB_PASSWORD=$(secret)
METABASE_DB_PASSWORD=$(secret)
METABASE_ENCRYPTION_KEY=$(secret)
ENV
mkdir -p .local/prod-transfer .local/backups .local/catalog/media .local/catalog/raw
echo ".env de production créé (permissions 600)."
