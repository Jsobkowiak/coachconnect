# Revue du catalogue initial

Source : Free Exercise DB, commit `f00c92c7dcf1216a928a52c3706c7ce8e2f71ed5`.
Le fichier `initial-quality.json` conserve les 14 décisions prises lors de cette
revue et leurs empreintes. Les décisions appliquées sont stockées dans MongoDB
(`quality_reviews`) ; ce fichier est un compte rendu, pas un import automatique.
L'auteur est `Codex`, sous l'autorisation de traitement qualité de l'utilisateur.

- 9 fiches : retrait des muscles secondaires déjà déclarés primaires par la source.
- 2 fiches : retrait d'une ligne de consigne vide, sans modifier les autres étapes.
- 3 fiches : variantes distinctes, conservées séparément (un/deux bras ;
  pronation/supination). Les consignes source confirment les distinctions.

Aucune consigne ni classification musculaire nouvelle n'a été inventée. Les
payloads bruts sont conservés sans modification. Une nouvelle version source
modifiant ces contenus demande une nouvelle revue.

Le catalogue passe de 857 à **871** exercices publiés. Les cinq fiches suivantes
restent rejetées car leurs listes de consignes sont entièrement vides :

- `Iron_Cross`
- `One-Arm_Kettlebell_Swings`
- `Push_Press`
- `Side_Bridge`
- `Side_Jackknife`

Il reste **77 avertissements** pour matériel non renseigné. Deux concernent des
fiches publiées à la suite de cette revue. Ils restent ouverts pour examen manuel.
Les commandes de revue sont décrites dans `../README.md` ; les décisions se
consultent aussi dans le tableau de bord Metabase.
