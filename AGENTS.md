# CoachConnect

- L’application sportive et l’authentification utilisent C# / ASP.NET Core 10. Le catalogue et l’ETL restent Python / FastAPI / Prefect / MongoDB.
- Le front sportif utilise React et TypeScript (`training-web/`). Thème clair uniquement, accents rouges ; navigation horizontale sur PC et barre compacte en bas sur mobile. Ne pas réintroduire de thème sombre.
- Deux usages prioritaires : **conception des blocs sur PC**, **saisie des performances mobile first pendant la séance**. Vérifier les deux formats.
- Programme prévu et séance réalisée sont des objets distincts. Modifier ou supprimer un bloc ne doit pas modifier l’historique des performances. Les instantanés et les contrôles de version sont obligatoires.
- L’application sportive possède sa propre authentification ASP.NET Core Identity intégrée. Ne pas la raccorder à un service d’authentification autonome. Toutes les données métier et les brouillons doivent rester isolés par compte ; préserver la récupération locale à usage unique des données antérieures.
- Conserver les données existantes. Les migrations de schéma doivent être additives et précédées d’une sauvegarde locale avant une bascule.
- Garder les règles métier hors des endpoints et des composants d’interface ; utiliser DI, requêtes SQL paramétrées et clients HTTP injectés. Conserver les contrats historiques des cycles pendant la migration.
- Ne pas exposer les secrets de `.env`, les clés privées ni les sauvegardes ; ne pas versionner `.local/`.
- Conserver les crédits et licences des illustrations. Aucun export massif des médias RepDB.
- Vérification : `dotnet build CoachConnect.sln`, `npm --prefix training-web run build`, tests HTTP auth/cycles/performances et parcours navigateur PC/mobile concernés.

- Le dépôt contient uniquement le socle actuel .NET / React / Python ; ne pas réintroduire les anciennes implémentations.
