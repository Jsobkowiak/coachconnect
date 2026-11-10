"""Read-only MongoDB questions seeded into the local Metabase instance."""

import json
from uuid import NAMESPACE_URL, uuid5


def joined(expression, separator=", "):
    return {
        "$reduce": {
            "input": expression,
            "initialValue": "",
            "in": {
                "$concat": [
                    "$$value",
                    {"$cond": [{"$eq": ["$$value", ""]}, "", separator]},
                    "$$this",
                ]
            },
        }
    }


def effective(field):
    return {"$ifNull": [f"$overrides.{field}", f"$source_data.{field}"]}


def text_tag(name, label):
    return {
        "id": str(uuid5(NAMESPACE_URL, "coachconnect:metabase:" + name)),
        "name": name,
        "display-name": label,
        "type": "text",
        "required": False,
    }


def questions():
    projection = {
        "$project": {
            "_id": 0,
            "Exercice": effective("name"),
            "Alias": joined(effective("aliases")),
            "Materiel": {"$ifNull": [effective("equipment"), "Non renseigné"]},
            "Categorie": effective("category"),
            "Muscles": joined(effective("primary_muscles")),
            "Niveau": effective("level"),
            "Consignes": joined(effective("instructions"), "\n"),
            "Id": "$_id",
        }
    }
    catalogue = (
        "[" + json.dumps(projection, ensure_ascii=False) + ",\n"
        '[[{"$match": {"Exercice": {"$regex": {{recherche}}, "$options": "i"}}},]]\n'
        '[[{"$match": {"Materiel": {{materiel}}}},]]\n'
        '[[{"$match": {"Categorie": {{categorie}}}},]]\n'
        '{"$sort": {"Exercice": 1}}]'
    )
    return [
        {
            "name": "Exercices disponibles",
            "collection": "exercises",
            "display": "scalar",
            "pipeline": [{"$count": "Exercices"}],
            "position": [0, 0, 8, 3],
        },
        {
            "name": "Anomalies bloquantes ouvertes",
            "collection": "quality_issues",
            "display": "scalar",
            "pipeline": [
                {"$match": {"status": "open", "severity": "error"}},
                {"$count": "Anomalies"},
            ],
            "position": [0, 8, 8, 3],
        },
        {
            "name": "Avertissements ouverts",
            "collection": "quality_issues",
            "display": "scalar",
            "pipeline": [
                {"$match": {"status": "open", "severity": "warning"}},
                {"$count": "Avertissements"},
            ],
            "position": [0, 16, 8, 3],
        },
        {
            "name": "Catalogue des exercices",
            "collection": "exercises",
            "display": "table",
            "query": catalogue,
            "tags": {
                "recherche": text_tag("recherche", "Rechercher un exercice"),
                "materiel": text_tag("materiel", "Matériel"),
                "categorie": text_tag("categorie", "Catégorie"),
            },
            "position": [3, 0, 24, 11],
        },
        {
            "name": "Exercices par catégorie",
            "collection": "exercises",
            "display": "bar",
            "pipeline": [
                {"$group": {"_id": effective("category"), "Exercices": {"$sum": 1}}},
                {"$project": {"_id": 0, "Categorie": "$_id", "Exercices": 1}},
                {"$sort": {"Exercices": -1}},
            ],
            "visualization_settings": {
                "graph.dimensions": ["Categorie"],
                "graph.metrics": ["Exercices"],
            },
            "position": [14, 0, 12, 6],
        },
        {
            "name": "Exercices par matériel",
            "collection": "exercises",
            "display": "bar",
            "pipeline": [
                {
                    "$group": {
                        "_id": {"$ifNull": [effective("equipment"), "Non renseigné"]},
                        "Exercices": {"$sum": 1},
                    }
                },
                {"$project": {"_id": 0, "Materiel": "$_id", "Exercices": 1}},
                {"$sort": {"Exercices": -1}},
            ],
            "visualization_settings": {
                "graph.dimensions": ["Materiel"],
                "graph.metrics": ["Exercices"],
            },
            "position": [14, 12, 12, 6],
        },
        {
            "name": "Anomalies à examiner",
            "collection": "quality_issues",
            "display": "table",
            "pipeline": [
                {"$match": {"status": "open"}},
                {
                    "$project": {
                        "_id": 0,
                        "Exercice_source": "$source_key",
                        "Type": "$kind",
                        "Severite": "$severity",
                        "Message": "$message",
                        "Derniere_detection": "$last_seen_at",
                    }
                },
                {"$sort": {"Severite": 1, "Exercice_source": 1}},
            ],
            "position": [20, 0, 24, 8],
        },
        {
            "name": "Historique des imports",
            "collection": "import_runs",
            "display": "table",
            "pipeline": [
                {"$sort": {"started_at": -1}},
                {"$limit": 100},
                {
                    "$project": {
                        "_id": 0,
                        "Debut": "$started_at",
                        "Statut": "$status",
                        "Source": "$source",
                        "Recuperes": "$summary.total",
                        "Ajoutes": "$summary.added",
                        "Modifies": "$summary.updated",
                        "Inchanges": "$summary.unchanged",
                        "Rejetes": "$summary.rejected",
                        "Doublons_suspects": "$summary.flagged",
                    }
                },
            ],
            "position": [28, 0, 24, 6],
        },
        {
            "name": "Historique des décisions qualité",
            "collection": "quality_reviews",
            "display": "table",
            "pipeline": [
                {"$sort": {"created_at": -1}},
                {
                    "$project": {
                        "_id": 0,
                        "Date": "$created_at",
                        "Exercice_source": "$source_key",
                        "Decision": "$action",
                        "Auteur": "$reviewer",
                        "Motif": "$note",
                        "Anomalie_id": "$_id",
                    }
                },
            ],
            "position": [34, 0, 24, 8],
        },
    ]
