# Infrastructure Docker

`compose.yaml` décrit les services, images, ports, dépendances et volumes. Le fichier `../../compose.yaml` est le point d’entrée qui l’inclut avec la racine du dépôt comme répertoire de projet. Toujours lancer les commandes depuis la racine, pour conserver la résolution de `.env`, des sources et des données locales.

```bash
docker compose --profile catalog --profile training up -d --build --wait training-app
docker compose --profile catalog --profile training ps
```

Profils : `training` (application et PostgreSQL), `catalog` (FastAPI, MongoDB et Prefect), `etl` (job d’import), `analytics` (Metabase et sa base). Les Dockerfiles restent auprès de leurs applications : `apps/backend/Dockerfile` et `apps/exercise-catalog/Dockerfile`.

Le projet s’appelle toujours `coachconnect`. Renommer les services ou volumes créerait une autre installation : conserver leurs noms lors des réorganisations du code. Les bases, clés, images et sauvegardes ne doivent pas entrer dans une image Docker ou dans Git. Ne pas utiliser `down -v` sur les données personnelles.
