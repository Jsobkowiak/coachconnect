# Copier un programme et composer une séance

Dans **Mes blocs**, le bouton **Copier vers un autre bloc** propose un destinataire et deux sources : toutes les semaines du programme, ou une semaine type à répéter. La copie remplace les séances prévues de toutes les semaines du destinataire après confirmation. Si les durées diffèrent, le dialogue explique la répétition ou la troncature. Dates, objectif, notes de semaine et marqueurs de semaine allégée du destinataire restent en place ; les charges doivent être adaptées manuellement aux semaines allégées. La sauvegarde conserve le contrôle de version du destinataire et l’isolation par compte.

Dans l’éditeur de séance, **Ajouter une partie** transforme les exercices existants en une première partie et ajoute la suivante. Chaque partie possède son nom, son format (force/classique, circuit, AMRAP, EMOM, for time), sa durée/time cap et ses consignes. Les flèches réordonnent les parties ; le sélecteur sur un exercice permet de changer sa partie. La suppression d’une partie et de ses exercices demande confirmation. Douze parties et soixante exercices au maximum par séance. Une séance d’un bloc actif ne peut pas contenir de partie vide.

Les parties et consignes apparaissent aussi dans **Ma séance** sur mobile. La saisie existante reste une saisie par exercice/série ; aucun score global de tours AMRAP ni chronomètre spécifique à chaque format n’est ajouté ici.

## Compatibilité et historique

Le contrat JSON conserve `session.exercises`. Les nouveaux champs sont facultatifs : `session.parts[]` (`id`, `title`, `format`, `timeCapMinutes`, `notes`) et `prescription.partId`. Sans parties, les anciens programmes conservent leur comportement. Avec parties, chaque prescription référence exactement une partie de la même séance. Le service valide ces références et ordonne la liste d’exercices selon les parties.

Les copies renouvellent les identifiants de séance, partie et prescription. Les séances réalisées conservent leur `plannedSession` figé : les modifications du programme ne réécrivent jamais cet instantané. Aucune migration SQL ni réécriture des documents existants n’est nécessaire.

## Vérification

- `dotnet build CoachConnect.sln`
- `npm --prefix apps/frontend run build`
- `TRAINING_URL=http://localhost:18081 python3 tests/integration/check-session-parts.py`
- `TRAINING_URL=http://localhost:18081 python3 tests/integration/check-programme-isolation.py`
- Avec Playwright installé : `TRAINING_URL=http://localhost:18081 python tests/e2e/check-session-parts-browser.py`
- Parcours historique : `tests/e2e/check-dotnet-browser.py` sur le même serveur de test.

Les contrôles utilisent un serveur authentifié avec une base jetable sur le port 18081. Le scénario navigateur crée uniquement des comptes de test dans cette base, qui doit être supprimée après vérification.
