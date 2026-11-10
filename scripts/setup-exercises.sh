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
for key in ['CATALOG_MONGO_ROOT_PASSWORD', 'CATALOG_MONGO_PASSWORD']:
    if key not in keys:
        new.append(key + '=' + secrets.token_hex(24))
if new:
    with p.open('a') as stream:
        if existing and not existing.endswith('\n'):
            stream.write('\n')
        stream.write('\n'.join(new) + '\n')
    p.chmod(0o600)
print('Configuration locale du catalogue prête ; secrets conservés dans .env.')
PY
mkdir -p .local/catalog/raw
docker compose --profile catalog up -d --build --wait catalog-mongo prefect catalog-api
