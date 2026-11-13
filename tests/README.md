# Tests transversaux

- `integration/` : tests des API HTTP réelles (authentification, cycles, performances, profil, mesures et statistiques).
- `e2e/` : parcours Playwright dans le navigateur, PC et mobile.
- `support/auth.py` : authentification des comptes de test. Les petits modules `training_test_auth.py` exposent ce helper aux scripts lancés directement.

Les tests unitaires propres au catalogue restent dans `apps/exercise-catalog/tests/`. Ceux du front restent dans `apps/frontend/tests/`.

Exécuter depuis la racine du dépôt, sur une application authentifiée utilisant une base **temporaire dédiée**, par exemple au port 18081 :

```bash
TRAINING_URL=http://localhost:18081 python3 tests/integration/check-programme-isolation.py
TRAINING_URL=http://localhost:18081 python3 tests/integration/check-training.py
TRAINING_URL=http://localhost:18081 python3 tests/integration/check-workouts.py
TRAINING_URL=http://localhost:18081 python3 tests/integration/check-session-parts.py
TRAINING_URL=http://localhost:18081 python3 tests/e2e/check-dotnet-browser.py
TRAINING_URL=http://localhost:18081 python3 tests/e2e/check-domain-navigation-browser.py
TRAINING_URL=http://localhost:18081 python3 tests/e2e/check-session-parts-browser.py
```

Les parcours E2E nécessitent Playwright et Chromium. Certains scénarios spécialisés utilisent une préparation privée explicite sous `.local/` ; lire leur en-tête avant exécution. Ne jamais lancer les tests d’écriture sur la base personnelle. Les assertions HTTP nutritionnelles restent pertinentes pour les contrats serveur conservés ; la rubrique Nutrition n’est plus exposée dans l’interface.

Pour le catalogue sans base réelle : depuis `apps/exercise-catalog`, lancer `uv sync --locked`, puis `uv run pytest -m 'not integration'`. Les tests MongoDB utilisent `scripts/check-exercises.sh` avec leurs propres bases temporaires.
