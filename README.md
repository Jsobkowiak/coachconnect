# CoachConnect

Monorepo personnel : conception des blocs sur PC et suivi des performances mobile first à la salle.

- `training-web/` : interface React / TypeScript / Vite (blocs, séances, exercices illustrés, profil et statistiques).
- `training-service/` : API C# / ASP.NET Core 10, PostgreSQL.
- `training-service/Features/Accounts/` : authentification sportive intégrée, ASP.NET Core Identity.
- `exercise-service/` : catalogue français, API Python/FastAPI, ETL Prefect et MongoDB.
- `analytics/` : Metabase.

## Démarrage WSL

Docker et Docker Compose suffisent pour exécuter les services. Pour développer hors Docker : SDK .NET 10 et Node 24.

```bash
./scripts/setup-training.sh
```

- Application : http://localhost:8081
- Statistiques : http://localhost:8081/#stats
- Carnet de séance : http://localhost:8081/#seance
- Exercices : http://localhost:8081/#illustrations
- Connexion sportive : http://localhost:8081/login
- Inscription sportive : http://localhost:8081/register

L’outil sportif possède sa propre authentification ASP.NET Core Identity intégrée. Les données sont isolées par compte ; l’ancien profil local est récupérable via le lien privé d’initialisation. Les ports sont locaux. Un téléphone réel nécessitera une configuration réseau et HTTPS dédiée ; son `localhost` n’est pas celui du PC.

Les identifiants locaux sont dans `.env`, ignoré par Git ; ceux existants sont conservés. Les comptes sportifs sont créés via l’inscription intégrée. Les volumes existants sont conservés ; aucun reset de base n’est requis.

## Développement et vérification

```bash
dotnet build CoachConnect.sln
npm --prefix training-web ci
npm --prefix training-web run dev
npm --prefix training-web run build
TRAINING_URL=http://localhost:18081 python3 scripts/check-training.py
TRAINING_URL=http://localhost:18081 python3 scripts/check-workouts.py
TRAINING_URL=http://localhost:18081 python3 scripts/check-programme-isolation.py
```

Le serveur Vite redirige `/api` vers ASP.NET (8081). Docker compile et sert le front sans serveur Node en production locale.

Voir [le schéma complet de l’architecture actuelle](docs/architecture-actuelle.md) (services, flux, stockage, ETL et état local au 5 novembre 2026).

Voir [l’architecture](docs/architecture.md), [les cycles et performances](training-service/README.md) et [le catalogue](exercise-service/README.md). Le catalogue français et ses illustrations restent accessibles via Python ; les imports et outils qualité existants sont conservés.

Les tests métier sur 18081 nécessitent un serveur de test et une base temporaire distincte. Ils créent des comptes authentifiés via les vrais endpoints ; aucun contournement de sécurité. Pour cibler un compte de test déjà créé, définir `TRAINING_TEST_EMAIL` et `TRAINING_TEST_PASSWORD`. Voir `training-service/README.md` pour l’initialisation, les sessions et la récupération des données locales.

## Versionnement

Voir [la gestion du code, des images et des données](docs/versioning.md). Le dépôt public contient le code et les ressources distribuables ; les données personnelles, secrets, sauvegardes et médias tiers téléchargés restent hors Git. La CI vérifie les builds et les tests Python, sans déploiement automatique.
