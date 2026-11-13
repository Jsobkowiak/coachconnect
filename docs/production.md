# Mise en production — joincoachconnect.com

Le VPS héberge déjà un Traefik (redirection HTTP → HTTPS, Let’s Encrypt). CoachConnect s’y raccorde par son réseau Docker : seul `training-app` est routé, sur `joincoachconnect.com` (`www` redirige en 301 vers le domaine nu). Bases, catalogue, Prefect et Metabase ne sont jamais publics.

```text
Internet ──443──▶ Traefik (VPS) ──réseau Docker──▶ training-app :8081 ──▶ training-db (PostgreSQL)
                                                                     └──▶ catalog-api ──▶ catalog-mongo
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `infrastructure/docker/compose.prod.yaml` | Surcouche : labels Traefik, HSTS, `restart`, aucun port publié, cookies `Secure`, IP client réelle |
| `scripts/prod/init-env.sh` | Crée le `.env` du VPS avec des secrets neufs |
| `scripts/prod/export-catalog.sh` | PC : exporte le catalogue (MongoDB + médias), sans donnée personnelle |
| `scripts/prod/restore-catalog.sh` | VPS : restaure cet export |
| `scripts/prod/backup.sh` | VPS : `pg_dump` de la base sportive, rotation 14 jours |
| `scripts/prod/deploy.sh` | VPS : mise à jour Git, sauvegarde, reconstruction, relance |

Le `.env` du VPS contient `COMPOSE_FILE` et `COMPOSE_PROFILES` : sur le VPS, `docker compose ps|logs|up` s’utilisent sans option.

## Première installation

Prérequis VPS : Docker, Compose ≥ 2.24 (`!reset`), Git, Python 3, et le nom du **réseau Docker** et du **certresolver** du Traefik existant (`docker network ls`, configuration de Traefik).

```bash
# 1. PC : exporter le catalogue
./scripts/prod/export-catalog.sh

# 2. VPS : cloner et configurer
git clone https://github.com/Jsobkowiak/coachconnect.git ~/coachconnect && cd ~/coachconnect
./scripts/prod/init-env.sh <reseau-traefik> <certresolver> [entrypoint]

# 3. PC : envoyer l’export
scp .local/prod-transfer/*<date>* <utilisateur>@<vps>:~/coachconnect/.local/prod-transfer/

# 4. VPS : restaurer puis démarrer
./scripts/prod/restore-catalog.sh .local/prod-transfer/catalog-<date>.archive.gz .local/prod-transfer/catalog-media-<date>.tar.gz
./scripts/prod/deploy.sh
```

La base sportive démarre vide ; l’inscription est ouverte (12 par heure et par IP, 30 connexions par minute et par IP). Aucun lien de récupération des données antérieures n’est configuré en production (`TRAINING_BOOTSTRAP_TOKEN_HASH` absent).

Sauvegarde nocturne (crontab du VPS) :

```cron
30 3 * * * cd ~/coachconnect && ./scripts/prod/backup.sh >> .local/backups/cron.log 2>&1
```

Copier régulièrement `.local/backups/` hors du VPS : une sauvegarde sur la même machine ne protège pas d’une perte du serveur.

## Livraisons suivantes

```bash
git tag v0.1.0 && git push origin v0.1.0     # PC, après CI verte
./scripts/prod/deploy.sh v0.1.0              # VPS
```

`deploy.sh` sauvegarde la base avant de reconstruire ; les volumes sont conservés. Consigner chaque MEP comme décrit dans [versioning.md](versioning.md). Ne jamais lancer `docker compose down -v` sur le VPS.

## Administration

- Logs : `docker compose logs -f training-app`
- Prefect / Metabase (profils non démarrés par défaut) : `ssh -L 4200:127.0.0.1:4200 <utilisateur>@<vps>`, puis http://localhost:4200.
- Restaurer une sauvegarde : `docker compose exec -T training-db pg_restore -U training -d coachconnect_training --clean < .local/backups/training-<date>.dump` (application arrêtée, procédure explicite uniquement).

## Contrôles après déploiement

```bash
curl -sI https://joincoachconnect.com | grep -i strict-transport   # HSTS
curl -sI https://www.joincoachconnect.com/blocs                     # 301 → domaine nu
curl -s  https://joincoachconnect.com/api/health                     # {"status":"ok"}
```

Puis parcours navigateur PC (conception d’un bloc) et mobile (saisie d’une séance).
