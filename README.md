# CoachConnect

Application personnelle pour concevoir ses blocs d’entraînement sur PC et saisir ses performances sur mobile. Interface React claire et rouge, API ASP.NET Core 10 avec authentification intégrée, catalogue d’exercices et ETL Python.

## Où travailler ?

```text
coachconnect/
├── apps/
│   ├── frontend/          # React / TypeScript : écrans et interactions
│   ├── backend/           # ASP.NET Core : auth, API et règles métier
│   └── exercise-catalog/  # Python : catalogue FastAPI, ETL et qualité
├── infrastructure/
│   ├── docker/            # Définition des services et volumes Docker
│   └── metabase/          # Configuration des tableaux de bord catalogue
├── tests/
│   ├── integration/       # Scénarios HTTP sur une base temporaire
│   ├── e2e/               # Parcours navigateur PC / mobile
│   └── support/           # Helpers d’authentification partagés
├── scripts/               # Démarrage, imports et maintenance
├── docs/                  # Architecture et procédures
├── .github/workflows/     # CI : compilation, tests et images Docker
├── compose.yaml           # Point d’entrée vers infrastructure/docker/
└── CoachConnect.sln       # Solution .NET
```

| Tu veux modifier… | Va dans… |
|---|---|
| Une page ou une interaction | [`apps/frontend/`](apps/frontend/README.md) |
| Une règle, un endpoint ou l’authentification | [`apps/backend/`](apps/backend/README.md) |
| Un exercice, une source ou un contrôle qualité | [`apps/exercise-catalog/`](apps/exercise-catalog/README.md) |
| Les conteneurs, ports ou volumes | [`infrastructure/docker/`](infrastructure/docker/README.md) |
| Les tableaux de bord Metabase | [`infrastructure/metabase/`](infrastructure/metabase/README.md) |
| Un scénario de vérification | [`tests/`](tests/README.md) |

## Démarrage depuis la racine du dépôt

Docker et Docker Compose suffisent pour les services. Compose doit prendre en charge `include` (2.20.0 ou plus récent).

```bash
./scripts/setup-training.sh
```

- Application : http://localhost:8081
- Connexion / inscription : http://localhost:8081/login et http://localhost:8081/register
- Carnet : http://localhost:8081/#seance
- Blocs : http://localhost:8081/#blocs
- Statistiques : http://localhost:8081/#stats

Pour les imports et la qualité : [guide du catalogue](apps/exercise-catalog/README.md).

Les commandes `docker compose` restent exécutées depuis la racine : `compose.yaml` charge la configuration rangée dans `infrastructure/docker/`. Le nom du projet Docker et les volumes persistants restent stables. Les secrets sont dans `.env`, les données locales et sauvegardes dans `.local/`, hors Git.

L’application sportive possède sa propre authentification Identity. Les données et brouillons sont isolés par compte ; la récupération locale à usage unique des données antérieures est préservée. Les ports sont locaux ; un téléphone physique nécessite une adresse réseau et HTTPS adaptés.

## Développement et vérification

SDK .NET 10, Node 24 et Python 3.12 avec uv pour le catalogue.

```bash
dotnet build CoachConnect.sln
npm --prefix apps/frontend ci
npm --prefix apps/frontend run dev
npm --prefix apps/frontend run build
```

Vite redirige `/api` vers ASP.NET sur 8081. Dans Docker, ASP.NET sert directement le front compilé : aucun serveur Node séparé.

Voir [les tests](tests/README.md), [les schémas d’architecture](docs/architecture-actuelle.md) et [le versionnement](docs/versioning.md). La CI n’effectue aucun déploiement automatique. Les bases réelles, secrets, sauvegardes et médias tiers téléchargés ne sont jamais publiés dans Git.
