# Principes d’architecture

Voir [les schémas détaillés](architecture-actuelle.md) et [le guide de versionnement](versioning.md).

## Composants actuels

- `training-web/` : React / TypeScript / Vite, thème clair et accents rouges. Navigation Entraînement et Suivi.
- `training-service/` : ASP.NET Core 10, authentification Identity intégrée, services métier injectés et accès PostgreSQL via Npgsql. EF Core gère les comptes Identity.
- `exercise-service/` : API FastAPI en lecture, catalogue français, imports Python / Prefect, validations et qualité des données MongoDB.
- `analytics/` : exploration du catalogue en lecture seule avec Metabase.

Le front compilé est servi par ASP.NET Core sur la même origine. Aucun jeton bearer n’est stocké dans le navigateur. Les comptes utilisent des cookies HttpOnly, des sessions serveur révocables et une protection antiforgery. Les clés Data Protection persistent dans un volume dédié.

## Deux usages

La conception des blocs est prioritaire sur PC : semaines, séances, parties ordonnées, exercices et prescriptions. La saisie des performances est conçue pour le mobile : séries, charges, repos et dernières performances. Un brouillon local propre au compte permet une reprise après rechargement ; il ne remplace pas l’enregistrement serveur et ne garantit pas un fonctionnement hors ligne complet.

## Invariants métier

- Le programme prévu et la réalisation sont des objets distincts. Une réalisation conserve son instantané du programme, même après modification ou suppression du bloc.
- Les fiches d’exercices sont récupérées et figées côté serveur. Le navigateur n’est pas une source de confiance pour les snapshots.
- Les écritures versionnées refusent les révisions périmées avec HTTP 409. Les identifiants client des nouvelles réalisations permettent le rejeu strict sans doublon.
- Les repositories filtrent les lectures et écritures par compte authentifié et utilisent du SQL paramétré.
- La récupération locale à usage unique des données antérieures reste disponible, sans réécriture des résultats.

## Statistiques et données

Les statistiques sont calculées dans .NET à partir des séances terminées et des mesures, puis rendues avec React/SVG. Leur lecture PostgreSQL utilise une transaction `REPEATABLE READ`. Les prescriptions imbriquées restent dans les documents JSONB des cycles ; le catalogue partagé reste dans MongoDB.

La rubrique Nutrition a été retirée de l’interface. Les contrats serveur et données historiques correspondants sont conservés pour compatibilité.

## Exploitation

Le Compose actuel est local, avec ports publiés sur `127.0.0.1`. L’accès depuis un téléphone physique et la MEP nécessitent une configuration réseau/HTTPS adaptée. Les volumes, clés, médias et sauvegardes restent hors Git. Toute évolution de schéma doit être additive et précédée d’une sauvegarde.

La CI construit .NET, React et les images Docker, et exécute les tests Python sans base réelle. Les tests HTTP et navigateur utilisent des bases temporaires distinctes. Les migrations Identity se créent avec `dotnet ef migrations add Nom --project training-service --context TrainingIdentityDbContext`.
