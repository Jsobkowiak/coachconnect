# Catalogue d'exercices et ETL

Ce dossier contient un projet Python avec deux points d'entrée : une API FastAPI
en lecture et un pipeline Prefect. L’authentification sportive est intégrée dans `../training-service/Features/Accounts/`.
MongoDB et Prefect sont auto-hébergés ; aucun compte cloud n'est nécessaire.

## Démarrer depuis la racine du dépôt

```bash
./scripts/setup-exercises.sh
./scripts/import-exercises.sh
```

Le premier script ajoute les secrets MongoDB manquants au `.env` existant sans
modifier ceux de l'auth. Il construit l'image Python et démarre MongoDB,
Prefect et l'API. Le deuxième exécute un import suivi dans Prefect.

- Documentation interactive de l'API : http://localhost:8001/docs
- Supervision Prefect : http://localhost:4200
- Catalogue : http://localhost:8001/exercises
- Anomalies : http://localhost:8001/quality-issues
- Bilans d'import : http://localhost:8001/import-runs

Les ports Docker sont publiés sur `127.0.0.1`. Ce socle est destiné au développement
local. L'API de catalogue et Prefect ne sont pas encore raccordés à l'auth ASP.NET Core.

## Source initiale

Le connecteur importe les données textuelles de
[Free Exercise DB](https://github.com/yuhonas/free-exercise-db), versionnées par un
commit Git immuable. Le commit par défaut figure dans `config.py`. Pour choisir
une version différente, passer un SHA complet de 40 caractères :

```bash
./scripts/import-exercises.sh --source-ref SHA_DU_COMMIT
```

Les fiches sont en anglais. Les noms, descriptions et classifications ne sont pas
des données médicalement certifiées : les contrôles vérifient leur structure et leur
cohérence selon nos règles. Le catalogue ne couvre pas encore tous les mouvements
CrossFit et n'importe pas de programmes/WOD.

Le dépôt source déclare une licence Unlicense. Sa provenance et le lien de licence
sont conservés à chaque import. Les images de cette source ne sont ni téléchargées ni publiées,
car leur origine fait l'objet de questions dans le dépôt source.

## Parcours des données

1. **Extraction** : HTTPX récupère le JSON du commit choisi ; Prefect retente jusqu'à
   trois fois l'extraction en cas d'erreur. Une copie complète, identifiée par son
   SHA-256, est conservée dans `.local/catalog/raw/` à la racine du dépôt.
2. **Données brutes** : chaque ligne est conservée dans `raw_exercises` avec sa
   position, son contenu d'origine et sa provenance. Un même snapshot rejoué ne
   multiplie pas les lignes.
3. **Transformation** : le connecteur mappe la structure source vers `ExerciseData`.
   Les catégories, muscles et matériels ont un vocabulaire contrôlé. Un matériel
   inconnu reste absent au lieu d'être inventé.
4. **Qualité** : Pydantic vérifie les champs, les listes non vides, les valeurs
   autorisées et les muscles primaires/secondaires distincts. Les ID source répétés
   sont tous rejetés. Un nom identique ou très proche avec même matériel et catégorie
   est signalé pour révision ; il n'est pas fusionné automatiquement.
5. **Chargement** : seuls les exercices acceptés sont publiés dans `exercises`.
   L'identité est stable, dérivée du couple source/ID source. Un hash permet de
   distinguer ajout, modification et contenu inchangé. Les corrections manuelles
   sont stockées séparément et conservées lors des imports suivants.

Les anomalies apparaissent dans `quality_issues`. Un équipement absent produit un
avertissement et n'empêche pas la publication. Une erreur ou un doublon suspect
empêche de publier la nouvelle fiche. Une ancienne version valide reste disponible
si une mise à jour est invalide. Rien n'est supprimé lorsqu'un exercice disparaît
de la source : une politique d'archivage sera ajoutée explicitement.

`import_runs` conserve statut, provenance et bilan : total, ajouts, modifications,
inchangés, rejets, doublons suspects et avertissements. `import_locks` empêche deux
imports simultanés de la même source, avec une lease de 30 minutes renouvelée pendant
le traitement. Si le processus est tué, cette lease expire ; l'exécution interrompue
peut rester marquée `running`. Un import échoué peut avoir chargé une partie des
fiches valides : rejouer l'import les retrouve sans les dupliquer.

Pour ajouter une source, créer un connecteur dans `sources/` et adapter explicitement
sa licence, son format et son mapping. Les alias bilingues et le rapprochement entre
sources sont des évolutions à construire ; les fiches textuelles proviennent actuellement de ce connecteur ; les visuels ont leur propre source ci-dessous.

## Correction manuelle

Créer un fichier JSON contenant uniquement les champs à corriger, par exemple :

```json
{"name": "Barbell Back Squat", "aliases": ["Squat arrière à la barre"]}
```

Puis le transmettre à la commande locale (l'ID vient de `/exercises`) :

```bash
docker compose --profile catalog --profile etl run --rm \
  -v "$PWD/correction.json:/tmp/correction.json:ro" catalog-etl \
  exercise-etl override ID_EXERCICE --file /tmp/correction.json
```

La correction est validée et appliquée à la lecture et aux filtres de l'API.
La revue se fait depuis WSL avec `scripts/review-exercises.sh`. Metabase reste en
lecture seule. Les commandes d'écriture ne sont pas exposées par l'API HTTP.

```bash
./scripts/review-exercises.sh list
./scripts/review-exercises.sh inspect ID_ANOMALIE
./scripts/review-exercises.sh decide ID_ANOMALIE distinct \
  --reviewer admin --note "Variante à deux bras, distincte de celle à un bras"
./scripts/review-exercises.sh decide ID_ANOMALIE acknowledge \
  --reviewer admin --note "Matériel non documenté, absence acceptée"
./scripts/review-exercises.sh decide ID_ANOMALIE correct \
  --reviewer admin --note "Suppression d'une ligne vide" --file correction-source.json
./scripts/import-exercises.sh
```

Pour `correct`, utiliser les **champs de la source** (`secondaryMuscles`,
`instructions`, etc.), par exemple `{"secondaryMuscles": ["glutes"]}`. Cette
commande concerne les fiches rejetées, tandis que `override` corrige les champs
normalisés d'une fiche déjà publiée. La correction est validée avant enregistrement.
L'identifiant source ne peut pas être modifié.

`quality_reviews` conserve la décision, l'auteur, le motif, le patch et l'empreinte
du contenu examiné. Une correction ou validation de variante est appliquée au
prochain import ; l'anomalie est résolue seulement après publication. Les décisions
sont immuables et un second enregistrement du même ID est refusé. Un avertissement
accepté est résolu immédiatement. Aucun exercice suspect n'est fusionné ou supprimé.

Les corrections de rejets sont liées au contenu brut exact ; les validations de
variantes sont liées au contenu normalisé et aux empreintes des candidats. Une
modification invalide ces décisions pour la nouvelle version et impose une nouvelle
revue. Les données brutes restent intactes. Les anomalies devenues obsolètes sont
clôturées après validation complète de la fiche.

L'API fournit aussi `/quality-issues/ID_ANOMALIE` (source et candidats) et
`/quality-reviews` (historique). Metabase affiche l'historique des décisions dans le
tableau de bord du catalogue.

## Développement et tests

Les dépendances sont verrouillées dans `uv.lock`. Avec [uv](https://docs.astral.sh/uv/)
installé dans WSL :

```bash
cd exercise-service
uv sync --locked
uv run pytest -m 'not integration'
uv run ruff check .
```

Pour tester les contraintes MongoDB, les imports rejoués, les corrections conservées
et l'API sur une base temporaire dédiée :

```bash
./scripts/check-exercises.sh
```

Les tests d'intégration créent et suppriment uniquement leurs propres bases
`coachconnect_test_*`. Le compte MongoDB normal du service ne peut écrire que dans
`coachconnect_exercises` ; les tests utilisent le compte administrateur local.

Prefect utilise ici une SQLite persistante dans son volume Docker, adaptée au socle
local. Les imports sont lancés à la demande. Aucun import récurrent n'est activé.
Une planification Prefect et une base PostgreSQL pour Prefect pourront être ajoutées
lorsque le besoin sera défini.

## Illustrations et rapprochement contrôlé

Trois connecteurs gratuits alimentent les illustrations, sans abonnement :

- [Everkinetic / Greg Priday](https://github.com/everkinetic/data), PNG sous CC BY-SA 4.0, commit figé.
- [RepDB](https://github.com/RepDB/exercise-dataset), WebP originaux générés par IA, commit figé. La licence Free Tier autorise l'affichage dans l'application avec « Exercise data by RepDB (repdb.co) ». Les fichiers premium sont exclus. Ne pas republier ces données comme catalogue téléchargeable ou API publique ; ne pas transformer les images par IA.
- [wger](https://wger.de/api/v2/exerciseinfo/), images sous licences CC sélectionnées individuellement. Le snapshot est identifié par SHA-256 ; auteur, licence et provenance sont conservés pour chaque image.

Les fichiers originaux sont vérifiés (format, dimensions, taille) puis stockés par
SHA-256 dans `.local/catalog/media/`. Le navigateur les lit localement ; les
crédits et la licence accompagnent chaque illustration dans son aperçu.

```bash
./scripts/import-exercise-media.sh
./scripts/review-exercise-media.sh list
./scripts/review-exercise-media.sh inspect ID_RAPPROCHEMENT
./scripts/review-exercise-media.sh approve ID_RAPPROCHEMENT ID_SOURCE \
  --reviewer admin --note "Mouvement, matériel et variante vérifiés"
./scripts/review-exercise-media.sh reject ID_RAPPROCHEMENT \
  --reviewer admin --note "La variante illustrée ne correspond pas"
```

L'import traite les trois sources par défaut. Pour une seule source :
`./scripts/import-exercise-media.sh --source repdb` (ou `everkinetic`, `wger`).
Les manifestes `data/*-links.json` contiennent uniquement des associations
examinées, liées au hash du contenu de l'exercice et à la version source.
Une similitude de nom propose un rapprochement mais ne publie jamais un visuel.
La revue compare matériel, posture, variante et images réelles. Les exclusions
RepDB documentées dans `data/repdb-media-exclusions.json` bloquent les images
incohérentes. Une illustration déjà validée reste prioritaire lors des imports.

Les sources gratuites ne couvrent pas toutes les variantes des 871 exercices.
La revue du 11 octobre 2026 couvre 266 exercices : 135 Everkinetic, 125 RepDB et
6 wger. Les 605 restants sont listés dans `.local/catalog/reports/missing-illustrations.csv`
et la synthèse est conservée dans `media-coverage.json` du même dossier.
`GET /media-coverage` donne la couverture réelle, par source, ainsi que le nombre
d'exercices restants avec des propositions en attente. L'interface expose les
filtres avec/sans illustration ; aucune image générique ne remplace un mouvement
sans correspondance validée. Les fichiers sans association restent privés au stockage.

Les collections `media_assets`, `media_sources` et `media_matches` conservent
provenance, crédit et décisions (auteur, motif, date). Les décisions sont immuables
et le rejeu ne duplique pas les associations. Une modification du contenu de
l'exercice invalide son ancien rapprochement : l'API masque alors le visuel et
l'import crée une nouvelle proposition à examiner. Une décision rejetée reste
rejetée lors d'un rejeu du même contenu.

API de lecture : `/exercises?with_media=true`, `/media-matches?status=pending`,
`/media-coverage`, `/media/assets/{sha256}.{png|jpg|webp}`. Pour sauvegarder le catalogue illustré, conserver
**MongoDB et `.local/catalog/media/`**, ainsi que les données brutes sous
`.local/catalog/raw/`. Les médias externes ne sont pas intégrés à Git ; les illustrations originales CoachConnect sont distribuées avec le code, dans `src/exercise_catalog/data/illustrations/`. En cas de perte
d'un fichier local, rejouer l'import restaure les images du commit conservé.

## Catalogue français rédigé

Le catalogue de l’application est désormais la révision française CoachConnect :
106 fiches françaises, toutes illustrées par des créations originales générées par IA dans un style commun (fond blanc, tenue grise et rouge, phases du mouvement). Les deux premières illustrations du push press et des pompes en pike sont conservées ; les 74 autres les rejoignent. Un lot de 30 exercices supplémentaires a été rédigé et illustré le 17 octobre 2026 ; les 76 fiches précédentes sont conservées. Les médias externes et les SVG historiques restent conservés dans les anciennes révisions avec leurs crédits et licences. Les prompts et contrôles sont dans `editorial/illustrations/generation.json`.
Les données importées restent disponibles via `?catalog=source`.
La rédaction, la publication atomique, les variantes et les sauvegardes sont
documentées dans [editorial/README.md](editorial/README.md).

```bash
./scripts/import-french-catalogue.sh
```
