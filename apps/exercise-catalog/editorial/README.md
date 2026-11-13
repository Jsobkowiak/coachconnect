# Catalogue français CoachConnect

Le catalogue publié contient **106 fiches françaises, toutes illustrées dans un style commun** : fond blanc, athlète en tenue grise et rouge, positions du mouvement. Les deux premières créations (push press et pompes en pike) sont conservées ; les 74 autres visuels ont été remplacés par des illustrations originales générées par IA. Les textes, identifiants et dates de rédaction des fiches sont conservés.

Le lot du **17 octobre 2026** ajoute 30 exercices : fentes arrière et marchées, squat bulgare et soulevés de terre avec haltères, machines unilatérales et des hanches, rowings avec appui thoracique, variantes aux poulies, tractions et dips lestés, gainage et abdominaux, Air Bike, SkiErg, marche du fermier et traîneau, développé militaire, développé incliné à la barre et extension de hanches sur banc. Les 76 fiches existantes restent inchangées. Les nouvelles fiches portent leur date de rédaction propre ; les illustrations sont contrôlées avant publication. Le vélo à air est distinct du crunch vélo au sol.

Les textes français sont rédigés pour CoachConnect. Ressources documentaires : [bibliothèque ACE](https://www.acefitness.org/resources/everyone/exercise-library/), [technique SkiErg de Concept2](https://www.concept2.com/blog/skierg-technique) et [marche du fermier CrossFit](https://www.crossfit.com/at-home/farmers-carry). Les références ne fournissent aucune image utilisée pour générer les visuels ; seule une illustration originale CoachConnect sert de référence de style.


Le premier lot contenait 73 fiches de musculation, haltérophilie et CrossFit,
rédigées le 11 octobre 2026. Chaque fiche comporte un nom français, des alias de
recherche anglais, le matériel détaillé, les muscles, quatre étapes et les erreurs
fréquentes. Les 73 fiches du premier lot étaient illustrées : 69 associations de visuels examinées,
et quatre schémas originaux simplifiés (burpee, wall ball, double under, pieds à la barre).
Les schémas montrent le geste ; ils ne sont pas des photographies.

Les SVG peuvent être régénérés depuis la racine du dépôt avec
`python3 apps/exercise-catalog/editorial/regenerate-diagrams.py`. Vérifier les dessins,
changer la version du JSON puis publier pour rendre les modifications visibles.

Le fichier de référence est `src/exercise_catalog/data/catalogue-fr.json`.
`exercices-fr.tsv` conserve le travail rédactionnel des 66 fiches liées au premier
catalogue. Modifier le JSON pour les publications suivantes et changer sa version.
Les quatre SVG historiques sont dans `src/exercise_catalog/data/diagrams/`, nommés
par SHA-256 et distribués sous CC BY 4.0, auteur CoachConnect. Les visuels externes
conservent leurs licences et crédits originaux (notamment RepDB, usage dans l'application).

```bash
./scripts/import-french-catalogue.sh
```

L'import valide **tout le lot** avant publication : schema, doublons, références
à la version examinée, disponibilité et empreinte des fichiers. Les révisions sont
stockées dans `coachconnect_exercises.curated_exercises`. Un pointeur atomique dans
`catalog_settings` sélectionne la révision visible. Les révisions antérieures restent
conservées ; rejouer le même fichier ne crée pas une nouvelle révision.
Les imports externes ne réécrivent ni les textes français ni leurs illustrations.
Les fiches françaises reprises du catalogue brut gardent leur identifiant, pour
préserver les exercices référencés dans les cycles. Les fiches créées ont un UUID stable.

La publication fait l'objet d'un contrôle éditorial des variantes et des images,
avec auteur, date et références ; ce statut ne signifie pas une certification par
un coach. La fraîcheur est la date réelle de rédaction/révision. Les anciennes
références externes ne sont pas présentées comme ayant été mises à jour aujourd'hui.

API : `/exercises` et `/media-coverage` utilisent ce catalogue français par défaut.
`/exercises?catalog=source` et `/media-coverage?catalog=source` donnent accès aux
871 fiches importées conservées. La recherche française ignore les accents et
accepte les alias anglais. Les anciens snapshots de séances restent historiques.

Sauvegarder MongoDB, `.local/catalog/media/` et ce dépôt (JSON, PNG et SVG compris).
Les fichiers RepDB ne doivent pas être redistribués comme un jeu de données public.

Les illustrations PNG originales sont versionnées dans `src/exercise_catalog/data/illustrations/`, sous leur SHA-256. Le fichier `editorial/illustrations/generation.json` conserve les prompts exacts, l’outil intégré utilisé et les chemins des fichiers. L’import vérifie l’empreinte, le type, les dimensions et la taille ; les crédits affichent explicitement la génération IA. Les snapshots des anciens cycles sont conservés : l’interface récupère le visuel actuel du catalogue pour chaque exercice, y compris lorsque le snapshot possède une ancienne image. Elle conserve l’image du snapshot en secours si le catalogue est indisponible. Seul l’affichage du média est actualisé ; les prescriptions et les performances ne sont pas réécrites.
