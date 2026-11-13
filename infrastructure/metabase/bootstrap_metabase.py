"""Idempotent local setup; credentials are read from .env and never printed."""

import json
from pathlib import Path

import httpx
from pymongo import MongoClient
from questions import questions

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "http://localhost:3000"
COLLECTION_NAME = "CoachConnect · Musculation"
DASHBOARD_NAME = "Catalogue et qualité des exercices"


def environment():
    return dict(
        line.split("=", 1)
        for line in (ROOT / ".env").read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    )


class Metabase:
    def __init__(self, secrets):
        self.secrets = secrets
        self.client = httpx.Client(base_url=BASE_URL, timeout=180)

    def request(self, method, path, payload=None):
        response = self.client.request(method, path, json=payload)
        if response.is_error:
            detail = response.text[:2000]
            for value in self.secrets.values():
                if len(value) >= 16:
                    detail = detail.replace(value, "[secret]")
            raise RuntimeError(
                f"Metabase {path}: HTTP {response.status_code}: {detail}"
            )
        return response.json() if response.content else None

    def authenticate(self):
        properties = self.request("GET", "/api/session/properties")
        token = properties.get("setup-token")
        if token:
            session = self.request(
                "POST",
                "/api/setup",
                {
                    "token": token,
                    "user": {
                        "email": self.secrets["METABASE_ADMIN_EMAIL"],
                        "password": self.secrets["METABASE_ADMIN_PASSWORD"],
                        "first_name": "Jonathan",
                        "last_name": "CoachConnect",
                    },
                    "prefs": {"site_name": "CoachConnect", "site_locale": "fr"},
                },
            )
        else:
            session = self.request(
                "POST",
                "/api/session",
                {
                    "username": self.secrets["METABASE_ADMIN_EMAIL"],
                    "password": self.secrets["METABASE_ADMIN_PASSWORD"],
                },
            )
        self.client.headers["X-Metabase-Session"] = session["id"]


def provision_mongo_reader(env):
    uri = (
        "mongodb://admin:"
        + env["CATALOG_MONGO_ROOT_PASSWORD"]
        + "@localhost:57017/?authSource=admin"
    )
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        db = client.coachconnect_exercises
        roles = [{"role": "read", "db": "coachconnect_exercises"}]
        exists = db.command("usersInfo", "metabase")["users"]
        db.command(
            "updateUser" if exists else "createUser",
            "metabase",
            pwd=env["METABASE_MONGO_PASSWORD"],
            roles=roles,
        )


def create_database(api, env):
    databases = api.request("GET", "/api/database")["data"]
    for database in databases:
        if database["name"] == "CoachConnect · Exercices":
            return database["id"]
    database = api.request(
        "POST",
        "/api/database",
        {
            "name": "CoachConnect · Exercices",
            "engine": "mongo",
            "is_full_sync": True,
            "details": {
                "host": "catalog-mongo",
                "port": 27017,
                "dbname": "coachconnect_exercises",
                "user": "metabase",
                "pass": env["METABASE_MONGO_PASSWORD"],
                "authdb": "coachconnect_exercises",
                "ssl": False,
            },
        },
    )
    return database["id"]


def create_collection(api):
    collections = api.request("GET", "/api/collection")
    for collection in collections:
        if collection["name"] == COLLECTION_NAME:
            return collection["id"]
    return api.request(
        "POST",
        "/api/collection",
        {
            "name": COLLECTION_NAME,
            "description": "Catalogue d’exercices et suivi de qualité.",
        },
    )["id"]


def seed_questions(api, database_id, collection_id):
    existing = api.request("GET", f"/api/collection/{collection_id}/items?models=card")[
        "data"
    ]
    saved = []
    for definition in questions():
        card = next(
            (item for item in existing if item["name"] == definition["name"]), None
        )
        if card is None:
            native = {
                "collection": definition["collection"],
                "query": definition.get("query") or json.dumps(definition["pipeline"]),
                "template-tags": definition.get("tags", {}),
            }
            card = api.request(
                "POST",
                "/api/card",
                {
                    "name": definition["name"],
                    "collection_id": collection_id,
                    "type": "question",
                    "display": definition["display"],
                    "visualization_settings": definition.get(
                        "visualization_settings", {}
                    ),
                    "dataset_query": {
                        "type": "native",
                        "database": database_id,
                        "native": native,
                    },
                },
            )
        saved.append((card["id"], definition))
    return saved


def seed_dashboard(api, collection_id, cards):
    items = api.request(
        "GET", f"/api/collection/{collection_id}/items?models=dashboard"
    )["data"]
    dashboard = next((item for item in items if item["name"] == DASHBOARD_NAME), None)
    if dashboard:
        current = api.request("GET", f"/api/dashboard/{dashboard['id']}")
        if current.get("dashcards"):
            # Add new quality views while preserving existing layout and filters.
            present = {item.get("card_id") for item in current["dashcards"]}
            additions = [
                (cid, definition) for cid, definition in cards if cid not in present
            ]
            if additions:
                row = max(item["row"] + item["size_y"] for item in current["dashcards"])
                dashcards = current["dashcards"]
                for index, (cid, definition) in enumerate(additions):
                    dashcards.append(
                        {
                            "id": -(index + 1),
                            "card_id": cid,
                            "row": row,
                            "col": 0,
                            "size_x": 24,
                            "size_y": 8,
                            "parameter_mappings": [],
                            "visualization_settings": {},
                            "series": [],
                        }
                    )
                    row += 8
                api.request(
                    "PUT", f"/api/dashboard/{dashboard['id']}", {"dashcards": dashcards}
                )
            return dashboard["id"]
    dashboard = dashboard or api.request(
        "POST",
        "/api/dashboard",
        {
            "name": DASHBOARD_NAME,
            "collection_id": collection_id,
            "description": "Les filtres s’appliquent au catalogue. Les indicateurs décrivent la base complète.",
            "parameters": [],
        },
    )
    parameters = [
        {
            "id": "recherche",
            "name": "Rechercher un exercice",
            "slug": "recherche",
            "type": "string/=",
            "sectionId": "string",
        },
        {
            "id": "materiel",
            "name": "Matériel",
            "slug": "materiel",
            "type": "string/=",
            "sectionId": "string",
        },
        {
            "id": "categorie",
            "name": "Catégorie",
            "slug": "categorie",
            "type": "string/=",
            "sectionId": "string",
        },
    ]
    dashcards = []
    for index, (card_id, definition) in enumerate(cards):
        row, col, width, height = definition["position"]
        mappings = [
            {
                "parameter_id": name,
                "card_id": card_id,
                "target": ["variable", ["template-tag", name]],
            }
            for name in definition.get("tags", {})
        ]
        dashcards.append(
            {
                "id": -(index + 1),
                "card_id": card_id,
                "row": row,
                "col": col,
                "size_x": width,
                "size_y": height,
                "parameter_mappings": mappings,
                "visualization_settings": {},
                "series": [],
            }
        )
    api.request(
        "PUT",
        f"/api/dashboard/{dashboard['id']}",
        {"parameters": parameters, "dashcards": dashcards},
    )
    return dashboard["id"]


def verify(api, cards, expected_count):
    results = {}
    for card_id, definition in cards:
        result = api.request(
            "POST", f"/api/card/{card_id}/query", {"ignore_cache": True}
        )
        if result.get("status") != "completed":
            raise RuntimeError(
                f"Question failed: {definition['name']}: {result.get('error')}"
            )
        rows = result["data"]["rows"]
        results[definition["name"]] = len(rows)
        if definition["name"] == "Exercices disponibles" and (
            not rows or rows[0][0] != expected_count
        ):
            raise RuntimeError("Metabase count differs from the catalogue count")
        if (
            definition["name"] == "Catalogue des exercices"
            and len(rows) != expected_count
        ):
            raise RuntimeError("The catalogue table does not contain all exercises")
        if definition["name"] == "Catalogue des exercices":
            filtered = api.request(
                "POST",
                f"/api/card/{card_id}/query",
                {
                    "ignore_cache": True,
                    "parameters": [
                        {
                            "id": definition["tags"]["recherche"]["id"],
                            "type": "category",
                            "target": ["variable", ["template-tag", "recherche"]],
                            "value": "squat",
                        },
                    ],
                },
            )
            if filtered.get("status") != "completed" or not filtered["data"]["rows"]:
                raise RuntimeError("The exercise search filter failed")
            cols = filtered["data"]["cols"]
            name_column = next(
                i for i, col in enumerate(cols) if col["name"] == "Exercice"
            )
            if any(
                "squat" not in row[name_column].lower()
                for row in filtered["data"]["rows"]
            ):
                raise RuntimeError("The search filter returned unrelated exercises")
    return results


def main():
    env = environment()
    provision_mongo_reader(env)
    api = Metabase(env)
    try:
        api.authenticate()
        database_id = create_database(api, env)
        collection_id = create_collection(api)
        cards = seed_questions(api, database_id, collection_id)
        dashboard_id = seed_dashboard(api, collection_id, cards)
        # Verify queries through Metabase, not just directly against MongoDB.
        uri = (
            "mongodb://metabase:"
            + env["METABASE_MONGO_PASSWORD"]
            + "@localhost:57017/coachconnect_exercises?authSource=coachconnect_exercises"
        )
        with MongoClient(uri) as client:
            count = client.coachconnect_exercises.exercises.count_documents({})
        results = verify(api, cards, count)
        dashboard = api.request("GET", f"/api/dashboard/{dashboard_id}")
        if not dashboard.get("dashcards"):
            raise RuntimeError("The dashboard contains no questions")
        catalogue = next(
            card
            for card in dashboard["dashcards"]
            if card.get("card", {}).get("name") == "Catalogue des exercices"
        )
        filtered = api.request(
            "POST",
            f"/api/dashboard/{dashboard_id}/dashcard/{catalogue['id']}/card/{catalogue['card_id']}/query",
            {
                "ignore_cache": True,
                "parameters": [
                    {"id": "recherche", "type": "string/=", "value": ["squat"]},
                    {"id": "materiel", "type": "string/=", "value": ["barbell"]},
                    {"id": "categorie", "type": "string/=", "value": ["strength"]},
                ],
            },
        )
        if filtered.get("status") != "completed" or not filtered["data"]["rows"]:
            raise RuntimeError("The dashboard filters failed")
        columns = {
            col["name"]: index for index, col in enumerate(filtered["data"]["cols"])
        }
        for row in filtered["data"]["rows"]:
            if (
                "squat" not in row[columns["Exercice"]].lower()
                or row[columns["Materiel"]] != "barbell"
                or row[columns["Categorie"]] != "strength"
            ):
                raise RuntimeError("The dashboard filters returned unrelated exercises")
        if httpx.get(f"{BASE_URL}/api/dashboard/{dashboard_id}").status_code != 401:
            raise RuntimeError("The dashboard is accessible without authentication")
        state = {
            "dashboard_url": f"{BASE_URL}/dashboard/{dashboard_id}",
            "dashboard_id": dashboard_id,
            "database_id": database_id,
            "collection_id": collection_id,
            "cards": results,
        }
        path = ROOT / ".local" / "metabase.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        print(
            f"Metabase prêt : {state['dashboard_url']} ({count} exercices, {len(cards)} questions)."
        )
        api.request(
            "DELETE",
            "/api/session",
            {"session_id": api.client.headers["X-Metabase-Session"]},
        )
    finally:
        api.client.close()


if __name__ == "__main__":
    main()
