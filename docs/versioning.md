# Versions du code, des services et des données

## Un monorepo

Le dépôt regroupe `training-web/`, `training-service/`, `exercise-service/`, `analytics/`, les scripts, migrations et fichiers Docker. Le front et le backend sportif sont construits ensemble ; le service Python fournit une autre image. Les bases utilisent les images officielles et des volumes persistants.

Git conserve le code, les contrats, migrations, règles de qualité, dépendances verrouillées, catalogue français éditorial et illustrations originales distribuables. Il ne conserve pas les bases réelles, les profils, performances, mensurations, sauvegardes, secrets ou médias externes téléchargés. Ces éléments restent dans les volumes Docker et `.local/`.

Le catalogue français versionné décrit des exercices, pas des données personnelles. Les licences et crédits des sources tierces restent applicables ; les médias RepDB ne doivent pas être exportés massivement. Rendre le dépôt public ne change pas ces licences.

## Flux de développement

- `main` : version de référence, livrable après vérification.
- `codex/nom-du-changement` : branche de travail.
- Pull request : changements lisibles et résultats CI avant intégration.
- Tag `v0.1.0`, `v0.1.1`, etc. : repère immuable d’une livraison validée. Ne pas déplacer un tag déjà publié.

Les contrôles CI construisent .NET et React, exécutent les tests Python sans base réelle et construisent les deux images Docker. Les tests HTTP et navigateur avec bases temporaires restent une étape de validation avant livraison ; la CI initiale ne les remplace pas. Aucun déploiement ou push d’image dans un registre n’est automatique pour l’instant.

## Images Docker

Une livraison associe le commit Git, le tag de version, les deux références d’images et, idéalement, leurs digests. Exemple de convention à mettre en place lors de la MEP : `coachconnect-training:v0.1.0` et `coachconnect-exercises:v0.1.0`. Le Compose local utilise encore `:local` ; il ne constitue pas un manifeste immuable de production.

Le code et ses dépendances entrent dans les images. Les données et secrets restent à l’extérieur. Reconstruire ou remplacer un conteneur ne doit pas supprimer son volume.

## Versions des données

- **PostgreSQL** : migrations de schéma dans Git ; données utilisateur uniquement dans la base et ses sauvegardes. Les évolutions restent additives, avec sauvegarde avant bascule.
- **MongoDB** : code des transformations et règles dans Git ; imports identifiés par leur source, version et empreinte, avec bilans d’exécution.
- **Sources brutes et médias externes** : snapshots/fichiers conservés hors Git avec leur provenance et leurs licences.
- **Retour arrière** : revenir à une ancienne image ne restaure pas une base et n’annule pas une migration. Vérifier la compatibilité du schéma ; restaurer une sauvegarde uniquement suivant une procédure explicite.

Pour chaque MEP, consigner : version Git, images, migrations appliquées, révision du catalogue et référence privée de la sauvegarde. Les sauvegardes réelles ne doivent jamais être attachées à une release publique.

## Dépôt public, écriture réservée au propriétaire

Le propriétaire du dépôt personnel reste seul à écrire tant qu’aucun collaborateur ou autre accès d’écriture n’est ajouté. Les visiteurs peuvent lire, cloner, créer un fork et proposer une pull request ; cela ne leur permet pas de modifier directement le dépôt. Les workflows CI ont uniquement `contents: read` et ne déploient rien.

L’identité des commits utilise l’adresse GitHub `noreply` pour éviter de publier l’adresse personnelle. Les fichiers `.env`, certificats, clés, dumps et fichiers générés sont exclus par `.gitignore`. Vérifier les fichiers préparés à chaque commit ; une exclusion Git ne retire pas un secret déjà publié dans l’historique.
