# Blocs et performances · ASP.NET Core

`./scripts/setup-training.sh`, puis http://localhost:8081. Front React dans `training-web/`, servi sur le même domaine que l’API C#.

**Sur PC**, créer des blocs, régler les dates et la durée, organiser les semaines et séances, prescrire les exercices et copier séances/semaines. Export JSON et duplication de bloc disponibles.

**Sur mobile**, ouvrir « Ma séance » (`/#seance`), sélectionner bloc/semaine/séance, saisir répétitions/charge ou temps/distance, valider chaque série et enregistrer. Un minuteur accompagne le repos et la dernière performance apparaît par exercice. Le record de charge des séries validées et enregistrées est affiché avec répétitions et date. À charge égale, le meilleur nombre de répétitions est retenu. Une amélioration dans la séance en cours reste signalée « à enregistrer » jusqu’à la sauvegarde ; les variantes d’exercices ne sont pas mélangées. Les brouillons sont conservés sur l’appareil ; les sauvegardes durables exigent le bouton Enregistrer/Terminer et un accès au serveur.

Données : PostgreSQL existante `coachconnect_training`, volume conservé. `training_cycles` garde son schéma ; `training_workouts` stocke les réalisations indépendantes et leur instantané du prévu. Révisions obligatoires pour les modifications et suppressions, HTTP 409 en cas de conflit. Le premier PUT d’un workout accepte un UUID stable pour un rejeu sans doublon. Les anciens exercices des cycles restent dans leurs snapshots.

Contrats principaux : `/api/cycles`, `/api/cycles/{id}`, `/api/cycles/{id}/duplicate`, `/api/workouts`, `/api/workouts/{id}`, `/api/catalog/exercises`, `/api/catalog/media-coverage`, `/api/catalog/media/assets/{filename}`. Le catalogue Python fournit les illustrations et leurs crédits, y compris Exercise data by RepDB (repdb.co).

Tests : `python3 scripts/check-training.py`, `python3 scripts/check-workouts.py` ; navigateur PC/mobile : `scripts/check-dotnet-browser.py` (Playwright requis).

L’authentification est intégrée au service sportif avec ASP.NET Core Identity et des cookies. Pour le découpage et les invariants, voir [l’architecture](../docs/architecture.md).

## Profil sportif

Le premier lancement demande un profil, modifiable depuis « Mon profil ». Chaque compte dispose de son propre profil. Le profil local antérieur est conservé et peut être rattaché à son propriétaire par la récupération initiale. Les tables additives `training_profiles` et `training_body_measurements` sont indépendantes des blocs et séances. Une sauvegarde PostgreSQL locale précède leur initialisation. Une mesure est ajoutée lors d’un changement de poids ou de taille, dans la même transaction que le profil. La révision protège les mises à jour concurrentes ; rejouer la création initiale identique ne duplique pas les mesures.

- `GET /api/profile` : profil, âge actualisé et estimations.
- `PUT /api/profile` : `{ revision, data }`, révision 0 à la création, 409 si conflit.
- `GET /api/profile/measurements` : les 100 dernières mesures.
- `GET /api/profile/estimates` : résultats dérivés réutilisables.

Le calcul adulte utilise la forme arrondie de [Mifflin–St Jeor](https://pubmed.ncbi.nlm.nih.gov/2305711/) : `10 × kg + 6,25 × cm − 5 × âge`, puis +5 (masculin) ou −161 (féminin). Paramètre non renseigné : fourchette des deux coefficients, sans inférence du genre. Les facteurs d’activité 1,4 / 1,6 / 1,8 / 2,0 sont des hypothèses de l’application, inspirées de la plage d’activité du [NIDDK](https://www.niddk.nih.gov/bwp). Ils incluent le sport ; le nombre de séances n’est pas ajouté au calcul. Les résultats sont arrondis à 10 kcal. Aucun déficit, surplus ni plan alimentaire automatique. Les estimations peuvent être désactivées et ne sont pas produites avant 18 ans. Les données historiques de performance ne sont jamais recalculées lors d’une mise à jour du profil.

`TRAINING_DB_NAME` permet d’exécuter les tests sur une base temporaire distincte, sans toucher au profil réel.

## Calories selon le bloc

La page « Calories » utilise le bloc prévu, le profil actuel et des réglages par séance. Les estimations ne modifient ni le bloc ni les performances réalisées.

- `GET /api/cycles/{id}/nutrition` recalcule les journées, semaines et l’ensemble du bloc.
- `PUT /api/cycles/{id}/nutrition` enregistre `{ revision, cycleRevision, dailyActivity, sessions: [{ sessionId, activity, durationMinutes }] }` dans `training_nutrition_settings`, table additive indépendante. Les révisions des réglages et du bloc protègent les mises à jour. Un bloc modifié déclenche une révision des hypothèses ; les réglages des séances supprimées sont ignorés à la lecture, les identifiants inconnus sont rejetés à l’écriture.

Les facteurs hors sport (1,4 / 1,6 / 1,8 / 2,0) sont des hypothèses de l’application. Le niveau global du profil, qui inclut le sport, n’est pas réutilisé pour additionner les séances. Pour une journée : `base = repos estimé × facteur hors sport`, `coût séances = Σ(MET × kg × heures)`, `maintien = max(base, base × (1 − heures séances / 24) + coût séances)`. Cette approximation remplace le coût moyen des heures déjà incluses dans la base, plutôt que de le compter deux fois. La somme des séances doit rester inférieure ou égale à 16 heures par journée. Aucune évolution de poids n’est prédite : le poids du profil actuel sert pour tout le bloc. Pas de déficit/surplus ni de conversion des charges/séries en calories.

Les MET proviennent du [Compendium 2024, conditionnement](https://pacompendium.com/conditioning-exercise/) : musculation modérée 3,5 (02054), soutenue 6 (02050), circuit modéré 5 (02035), circuit soutenu 7,5 (02040), rameur modéré 5 (02071), SkiErg lent/modéré 10,5 (02082) ; [course](https://pacompendium.com/running/) : environ 6,5 km/h à 6,5 MET (12028) ou 8 km/h à 8,5 MET (12030). L’intensité moyenne doit couvrir la durée saisie, pauses comprises ; les pointes d’effort ne sont pas extrapolées à la totalité d’une séance.

Une séance de musculation détaillée propose l’effort modéré ; un format circuit détaillé propose un circuit modéré. Ce sont des hypothèses visibles et modifiables. Les séances vides, les séances cardio traditionnelles et les catégories inconnues attendent une sélection explicite. Le titre « WOD », « Hyrox » ou « zone 2 » ne suffit pas pour inventer une intensité. Les jours incomplets ne sont pas présentés comme des jours de repos et leurs moyennes hebdomadaires/globales restent nulles. Les dates restent nulles sans date de début du bloc. Un badge deload ne change pas implicitement durée ou intensité. Les chiffres sont affichés à 10 kcal près, tandis que les calculs intermédiaires conservent leur précision.

## Carnet de mensurations

Dans « Mon profil », « Ajouter une mesure » enregistre un relevé daté indépendant : poids, stature, taille, hanches, poitrine, bras/cuisses/mollets gauche et droit. Chaque champ est facultatif ; un relevé doit contenir au moins une valeur. Les guides « Où mesurer ? » précisent les repères et conditions. Les anciennes mesures de profil restent consultables sans modification.

- `GET /api/profile/body-measurements` : tous les relevés, triés par date de mesure puis date d’enregistrement.
- `POST /api/profile/body-measurements` : `{ id, measuredOn, values, notes, updateProfile, profileRevision }`. `values` accepte `weightKg`, `heightCm`, `waistCm`, `hipsCm`, `chestCm`, `armLeftCm`, `armRightCm`, `thighLeftCm`, `thighRightCm`, `calfLeftCm`, `calfRightCm`. Dates ISO, kg/cm, deux décimales maximum. Dates futures rejetées.

La table additive `training_measurement_entries` conserve ces relevés sans modifier les blocs ni leurs instantanés. L’identifiant fourni par le client rend le rejeu identique sans doublon ; un contenu différent avec le même identifiant renvoie 409. Les corrections se font par un nouveau relevé annoté, sans réécriture de l’historique.

`updateProfile` est facultatif et désactivé par défaut. Il exige une mesure d’aujourd’hui (Europe/Paris), un poids ou une stature, ainsi que la révision actuelle du profil. Le relevé, la mise à jour du profil et son historique sont enregistrés dans une seule transaction. Les pages de calories utilisent ensuite le profil actualisé. Une mesure antidatée ne peut pas actualiser le profil. Le contrat historique `/api/profile/measurements` est conservé.

Tests sur serveur isolé : `MEASUREMENTS_TEST_URL=http://localhost:18081 python3 scripts/check-measurements.py` et `scripts/check-measurements-browser.py` (Playwright). Le test HTTP attend un profil de test préexistant ; aucun de ces scripts ne doit être dirigé vers la base réelle.

## Statistiques de progression

La page « Stats » (`/#stats`) propose trois vues : exercice, mensurations, régularité. Filtres sur 1, 3, 6, 12 mois ou tout l’historique ; filtre des séries par plage de répétitions. Graphiques interactifs au survol, au curseur tactile/clavier et tableaux accessibles des valeurs.

`GET /api/stats?months=3&minReps=6&maxReps=10` est une lecture seule, calculée dans `StatsService` à partir d’un instantané cohérent PostgreSQL. Aucun schéma ni historique n’est modifié. Les paramètres de répétitions sont facultatifs et ne filtrent que les séries en répétitions.

- Seules les séances terminées, jusqu’à la date actuelle à Paris, et les séries validées avec une performance positive entrent dans les courbes par exercice. Les séances en cours sont comptées à part. Aucun point ne vient des prescriptions futures ou des brouillons de l’appareil.
- Les identifiants d’exercice et les modes répétitions/temps/distance restent distincts. Les instantanés des séances fournissent les noms même après suppression d’un bloc. Les séries d’un même exercice/mode et d’une même date sont regroupées.
- Charge maximale avec répétitions associées, meilleure série de répétitions et répétitions totales, nombre de séries, volume externe, durées et distances. Le volume est absent pour une journée si une charge manque parmi les séries retenues. Le poids du corps et les estimations de 1RM ne sont pas ajoutés.
- Les courbes corporelles reprennent tout l’historique du profil, au-delà des 100 lignes de son ancien endpoint. Un relevé explicite du carnet prend priorité sur le profil pour une même date/mesure ; le dernier relevé explicite de la journée est retenu. Les champs absents ne sont pas des zéros.
- Écart premier/dernier point observé et comparaison de moyennes sur deux fenêtres calendaires fixes de 28 jours. Chaque moyenne exige trois dates distinctes dans sa fenêtre. Sans assez de données, la comparaison reste à compléter. Ces chiffres ne diagnostiquent pas un plateau et ne déclenchent aucune modification d’entraînement ou de nutrition.
- Régularité : séances terminées par semaine lundi–dimanche, semaines vides à zéro, limites de période potentiellement partielles.

Tests dédiés en base temporaire : `STATS_TEST_URL=http://localhost:18081 python3 scripts/check-stats.py` (base initialement vide) et `scripts/check-stats-browser.py` (fixture créée par le test HTTP, Playwright requis). Les scénarios contrôlent aussi l’absence de toute mutation des données.


## Authentification intégrée

Les formulaires React de connexion et d’inscription sont servis par l’application sportive elle-même (`/login`, `/register`). Aucune redirection vers l’ancien service d’authentification ni dépendance à un fournisseur externe. `Mon compte` permet de se déconnecter et de changer le mot de passe.

ASP.NET Core Identity gère les mots de passe (12–128 caractères, au moins 4 caractères distincts), normalisation/uniquité des e-mails et verrouillage après 5 erreurs pendant 15 minutes. Les comptes et migrations EF utilisent le schéma séparé `training_identity` dans la base sportive. Les cookies HttpOnly/SameSite ne contiennent qu’une référence à une session révocable côté serveur. Les tickets sont chiffrés avec Data Protection ; les clés persistent dans le volume `training-auth-keys` et doivent être sauvegardées avec la base. Durée de session : 12 heures, ou 14 jours avec « Rester connecté », renouvellement glissant. La déconnexion révoque la session courante ; un changement de mot de passe révoque toutes les sessions.

- `GET /api/auth/session` (public) : utilisateur courant ou `null`, jeton antiforgery, disponibilité de récupération locale.
- `POST /api/auth/register`, `POST /api/auth/login` (publics) : `{ email, password, rememberMe }`.
- `POST /api/auth/logout`, `POST /api/auth/password` (`{ currentPassword, newPassword }`) et `POST /api/auth/claim` (`{ token }`) nécessitent une session.
- Tous les POST/PUT/DELETE nécessitent `X-CSRF-TOKEN`, y compris connexion/inscription. Récupérer un nouveau jeton depuis `/auth/session` après changement de compte. Les autres API métier exigent une session et répondent 401/403 sans redirection HTML. `/api/health` reste public.
- Le client envoie `X-Training-User` pour empêcher qu’une opération d’un ancien onglet s’applique à un autre compte connecté entre-temps. Les brouillons locaux utilisent une clé par compte ; les données affichées sont retirées à l’expiration de session.

Les colonnes `owner_id` ajoutées aux blocs, séances, profils et réglages caloriques ne changent ni leurs documents ni leurs révisions. Toutes les requêtes sont filtrées par compte ; les mensurations héritent de celui du profil. Les identifiants de données appartenant à un autre compte répondent 404. Les statistiques filtrent leurs sources avant agrégation.

### Récupération du profil local antérieur

`python3 scripts/prepare-training-auth.py` (appelé par `setup-training.sh`) prépare un secret local et son empreinte SHA-256 sans les afficher. Le lien privé est enregistré dans `.local/training-auth/initialisation.url`. Il ouvre l’inscription/connexion puis une étape explicite de récupération. Le secret est retiré du fragment d’URL dès son chargement et supprimé du stockage de session après utilisation.

La récupération nécessite un compte authentifié sans profil et le code local à usage unique. Une transaction attribue les données non encore possédées, sans changer leurs identifiants, documents, dates ou versions. Un autre compte inscrit en premier ne reçoit aucune donnée historique. L’ancien brouillon partagé du navigateur n’est repris que par le propriétaire de ces données. Les données restent conservées et inaccessibles tant que le propriétaire n’a pas créé son compte et confirmé la récupération. Ne pas publier le lien/code, les clés ou les sauvegardes.

### Configuration et tests

Le déploiement fourni reste lié à `127.0.0.1`. Pour un déploiement HTTPS adapté, configurer `TRAINING_HTTPS=true` (cookies Secure) et le proxy de confiance. Les limites par IP sont réglables avec `TRAINING_LOGIN_RATE_LIMIT` (30/minute) et `TRAINING_REGISTRATION_RATE_LIMIT` (12/heure, inscription et récupération). Les tests temporaires peuvent les augmenter sans désactiver aucune protection. L’envoi et la vérification d’e-mails ainsi que la récupération de mot de passe par e-mail ne sont pas configurés ; aucun écran ne simule un envoi.

`ACCOUNTS_TEST_URL=http://localhost:18081 python3 scripts/check-training-accounts.py` et `scripts/check-training-accounts-browser.py` utilisent exclusivement une base temporaire. Ils vérifient les sessions, CSRF, récupération, changement de mot de passe et l’isolation sur toutes les fonctionnalités. Les scripts métier utilisent `training_test_auth.py` : sur 18081, ils créent de vrais comptes de test ; ailleurs, définir explicitement `TRAINING_TEST_EMAIL` et `TRAINING_TEST_PASSWORD` pour un compte de test dédié. Il n’existe aucun mode de contournement de l’authentification.


## Navigation par domaine et anciens relevés

La navigation principale comporte trois domaines : Entraînement (Ma séance, Mes blocs, Exercices), Suivi (Stats, Mon profil), Nutrition (Calories). Seules les rubriques du domaine actif sont affichées. Chaque domaine retrouve son dernier écran ; l’accès Entraînement ouvre par défaut les blocs sur PC et la séance sur mobile. Les contrôles de modifications non enregistrées restent appliqués avant tout changement de domaine.

Les relevés corporels acceptent `datePrecision: "day"` (défaut historique) ou `"month"`. En précision mensuelle, `measuredOn` utilise le premier du mois comme ancrage technique, sans prétendre connaître le jour réel. L’interface affiche seulement le mois et l’année ; ces points ne participent pas aux moyennes sur 28 jours. Les mesures d’un mois et celles d’un jour précis restent distinctes.

Champs complémentaires : `neckCm`, `armUnspecifiedCm` (côté et contraction inconnus), `armFlexedCm` (contracté, côté inconnu), `thighCm` et `calfCm` (côté inconnu). Ne jamais recopier un relevé sans côté dans gauche et droite, ni comparer un bras contracté avec une mesure de contraction inconnue.

La commande administrative locale `dotnet CoachConnect.Training.dll --import-measurements adresse@example.test` lit une liste JSON de `MeasurementInput` sur stdin. Elle trouve un compte existant et son profil, passe par le service métier et ajoute des identifiants stables, sans créer de session ni changer le profil actuel. Aucun endpoint HTTP ne permet ce mode administratif. Un relevé de référence explicitement demandé jusqu’à sept jours à venir peut être importé ; il est signalé dans le carnet et exclu des courbes jusqu’à sa date. Les API publiques conservent le refus des dates futures. Conserver la sauvegarde et les fichiers d’import en dehors du dépôt versionné.

Dans Stats, le front ouvre toute la période par défaut. `includeReferenceMeasurements=true` permet de comparer aussi les relevés du carnet dont la date de référence est à venir ; chaque point concerné est signalé dans son détail. Sans ce paramètre, le contrat historique exclut ces dates. Cette option ne concerne ni les performances ni les moyennes sur 28 jours et ne modifie aucune mesure enregistrée.

### Objectif calories et macros

`GET /api/nutrition/target` lit l’objectif du compte connecté (ou `null`). `POST /api/nutrition/target/preview` calcule sans écrire ; `PUT /api/nutrition/target` enregistre avec contrôle `revision` (0 pour la création, puis révision courante). Les entrées sont `startDate`, `weightKg`, `maintenanceKcal`, `deficitKcal`, `proteinPerKg`, `fatPerKg`, `maintenanceSource` (`estimated` ou `observed`). La cible est maintien − déficit ; protéines et lipides sont arrondis au gramme, puis les glucides complètent à 4/4/9 kcal par gramme. Le poids est un instantané explicite ; les changements de profil ou de bloc ne modifient pas rétroactivement l’objectif. Aucun repas consommé n’est déduit de cette cible.

La table additive `training_macro_targets` appartient directement au compte Identity et reste séparée des réglages de dépense des blocs. Sauvegarder PostgreSQL avant la première mise à jour. L’administration locale peut enregistrer un objectif validé avec `dotnet CoachConnect.Training.dll --set-nutrition-target email`, JSON sur stdin, sans connexion ni modification du profil ou des mensurations.
