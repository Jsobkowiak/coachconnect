# Metabase local

Metabase est disponible sur http://localhost:3000, avec une connexion propre à
Metabase. Le compte initial est `admin@coachconnect.local` ; son mot de passe
généré se trouve dans `.env` sous `METABASE_ADMIN_PASSWORD`.
L'adresse est un identifiant local, aucun email n'est envoyé.

## Installer et démarrer

Après installation des dépendances Python du catalogue :

```bash
./scripts/setup-metabase.sh
```

Le script démarre Metabase et sa PostgreSQL dédiée, crée un utilisateur MongoDB
en lecture seule, configure la connexion au catalogue et initialise les questions
et le tableau de bord. Les questions existantes et les modifications du tableau de
bord sont conservées lorsqu'on relance le script. Les liens et identifiants des
ressources créées sont enregistrés dans `.local/metabase.json`.

Le tableau de bord **Catalogue et qualité des exercices**, dans la collection
**CoachConnect · Musculation**, contient :

- La liste des exercices avec recherche, matériel et catégorie.
- Les nombres d'exercices, d'anomalies bloquantes et d'avertissements.
- Les répartitions par catégorie et matériel.
- Les anomalies à examiner, l'historique des imports et les décisions qualité.

Les filtres du tableau de bord concernent la liste des exercices. Les indicateurs
globaux restent ceux de la base entière. Pour le matériel et la catégorie, utiliser
les codes du catalogue, par exemple `barbell`, `dumbbell`, `bodyweight`, `strength`
ou `stretching`. La recherche du nom est insensible à la casse et accepte des
expressions régulières MongoDB. Les fiches respectent les corrections manuelles
conservées par l'ETL. Les valeurs des muscles, catégories et matériels restent en anglais.

Les vues interrogent MongoDB directement : les nouveaux imports sont visibles en
rafraîchissant les questions. Metabase ne sert pas à modifier le catalogue ; utiliser
les commandes `scripts/review-exercises.sh` décrites dans `apps/exercise-catalog/README.md`.
Les nouvelles vues du bootstrap sont ajoutées en bas du tableau de bord en conservant
les cartes et filtres existants.

## Stockage et accès

- Image Metabase Community figée à `v0.64.1`.
- PostgreSQL dédiée dans le volume `metabase-db-data` pour les utilisateurs,
  connexions, questions et tableaux de bord.
- Utilisateur MongoDB `metabase` avec le rôle `read` uniquement sur
  `coachconnect_exercises`.
- Port publié sur `127.0.0.1:3000`, sans lien public de partage activé.
- Secrets et clé de chiffrement des connexions conservés dans `.env`.

Sauvegarder ensemble la base PostgreSQL Metabase et sa clé `METABASE_ENCRYPTION_KEY`.
Le compte Metabase est distinct de l'auth ASP.NET Core. Le SSO OpenID Connect n'est pas configuré.

Le bootstrap vérifie les neuf questions via l'API Metabase, le nombre d'exercices,
la recherche `squat` et le refus d'accès aux données du tableau de bord sans connexion.
