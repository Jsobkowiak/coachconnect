#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('.env')
existing = p.read_text() if p.exists() else ''
keys = {line.split('=', 1)[0] for line in existing.splitlines() if '=' in line}
new = []
for key in ['AUTH_DB_PASSWORD', 'CATALOG_MONGO_ROOT_PASSWORD', 'CATALOG_MONGO_PASSWORD',
            'METABASE_DB_PASSWORD', 'METABASE_MONGO_PASSWORD', 'METABASE_ENCRYPTION_KEY']:
    if key not in keys:
        new.append(key + '=' + secrets.token_hex(24))
if 'METABASE_ADMIN_EMAIL' not in keys:
    new.append('METABASE_ADMIN_EMAIL=admin@coachconnect.local')
if 'METABASE_ADMIN_PASSWORD' not in keys:
    new.append('METABASE_ADMIN_PASSWORD=' + secrets.token_urlsafe(24) + 'Aa1!')
if new:
    with p.open('a') as stream:
        if existing and not existing.endswith('\n'):
            stream.write('\n')
        stream.write('\n'.join(new) + '\n')
    p.chmod(0o600)
print('Configuration Metabase prête ; identifiants conservés dans .env.')
PY
docker compose --profile catalog --profile analytics up -d --wait metabase-db metabase
if [[ -x exercise-service/.venv/bin/python ]]; then
  exercise-service/.venv/bin/python analytics/bootstrap_metabase.py
else
  echo 'Installe les dépendances Python du catalogue avant de configurer Metabase.' >&2
  exit 1
fi
