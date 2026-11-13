# Frontend — React / TypeScript

Cette application gère uniquement l’interface : conception des blocs sur PC, saisie des performances sur mobile, catalogue, profil et statistiques. Le thème est clair, avec accents rouges.

- `src/features/` : écrans regroupés par fonctionnalité (`accounts`, `blocks`, `workouts`, `catalog`, `profile`, `stats`). `nutrition` est conservé pour référence de compatibilité mais n’est plus importé par l’application.
- `src/shared/` : client HTTP, types et icônes partagés.
- `src/App.tsx` : navigation Entraînement / Suivi et assemblage des écrans.
- `tests/` : tests unitaires locaux au front. Les parcours navigateur sont dans `../../tests/e2e/`.

Depuis la racine : `npm --prefix apps/frontend run dev` ou `npm --prefix apps/frontend run build`.

Les règles d’autorisation et de validation métier restent dans le backend. Les brouillons de séance sont isolés par compte et ne remplacent pas la sauvegarde serveur. Le front compilé est livré dans l’image Docker sportive, sur la même origine que l’API.
