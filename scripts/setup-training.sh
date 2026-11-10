#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]] || ! rg -q '^CATALOG_MONGO_PASSWORD=' .env; then
  ./scripts/setup-exercises.sh
fi
python3 - <<'PY'
from pathlib import Path
import secrets
path=Path('.env')
text=path.read_text()
if not any(line.startswith('TRAINING_DB_PASSWORD=') for line in text.splitlines()):
    with path.open('a') as file:
        file.write('\nTRAINING_DB_PASSWORD='+secrets.token_hex(24)+'\n')
PY
python3 scripts/prepare-training-auth.py
docker compose --profile catalog --profile training up -d --build --wait training-db training-app
python3 - <<'PY'
import time, urllib.request
for attempt in range(60):
    try:
        urllib.request.urlopen('http://localhost:8081/api/health',timeout=2)
        break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit('Le service training ne répond pas. Consulter docker compose logs training-app.')
print('Conception des cycles : http://localhost:8081')
PY
