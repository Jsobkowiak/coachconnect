from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.errors import CollectionInvalid, DuplicateKeyError

from exercise_catalog.config import Settings
from exercise_catalog.models import Equipment, Muscle


def now():
    return datetime.now(UTC)


def connect(config: Settings):
    client = MongoClient(
        config.mongo_uri.get_secret_value(), serverSelectionTimeoutMS=5000, tz_aware=True
    )
    return client, client[config.database]


def initialize(db):
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "_id",
                "source_key",
                "source_data",
                "provenance",
                "content_hash",
                "overrides",
            ],
            "properties": {
                "_id": {"bsonType": "string"},
                "source_key": {"bsonType": "string"},
                "content_hash": {"bsonType": "string"},
                "overrides": {"bsonType": "object"},
                "provenance": {"bsonType": "object"},
                "source_data": {
                    "bsonType": "object",
                    "required": [
                        "name",
                        "primary_muscles",
                        "instructions",
                        "equipment",
                        "category",
                    ],
                    "properties": {
                        "name": {"bsonType": "string", "minLength": 2},
                        "equipment": {"enum": [None, *[e.value for e in Equipment]]},
                        "primary_muscles": {
                            "bsonType": "array",
                            "minItems": 1,
                            "items": {"enum": [m.value for m in Muscle]},
                        },
                        "instructions": {
                            "bsonType": "array",
                            "minItems": 1,
                            "items": {"bsonType": "string", "minLength": 1},
                        },
                    },
                },
            },
        }
    }
    try:
        db.create_collection("exercises", validator=validator)
    except CollectionInvalid:
        pass  # Future validator changes require an explicit database migration.
    db.exercises.create_index("source_key", unique=True)
    db.exercises.create_index("normalized_name")
    db.exercises.create_index(
        [("source_data.equipment", ASCENDING), ("source_data.primary_muscles", ASCENDING)]
    )
    db.raw_exercises.create_index(
        [("source", ASCENDING), ("snapshot_sha256", ASCENDING), ("position", ASCENDING)],
        unique=True,
    )
    db.quality_issues.create_index([("status", ASCENDING), ("source_key", ASCENDING)])
    db.quality_reviews.create_index(
        [("source_key", ASCENDING), ("action", ASCENDING), ("raw_hash", ASCENDING)]
    )
    db.media_sources.create_index(
        [("source_ref", ASCENDING), ("source_id", ASCENDING)], unique=True
    )
    db.media_matches.create_index([("status", ASCENDING), ("exercise_id", ASCENDING)])
    db.curated_exercises.create_index([("revision", ASCENDING), ("exercise_id", ASCENDING)], unique=True)
    db.import_runs.create_index("started_at")


def acquire_lock(db, source: str, run_id: str):
    """A bounded lease prevents two imports of the same source from interleaving."""
    try:
        lock = db.import_locks.find_one_and_update(
            {"_id": source, "$or": [{"expires_at": {"$lt": now()}}, {"owner": run_id}]},
            {"$set": {"owner": run_id, "expires_at": now() + timedelta(minutes=30)}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError as error:
        raise RuntimeError("An import of this source is already running") from error
    return lock


def stable_id(source_key: str) -> str:
    return str(uuid5(NAMESPACE_URL, "coachconnect:exercise:" + source_key))


def start_run(db, source: str, source_ref: str) -> str:
    run_id = str(uuid4())
    db.import_runs.insert_one(
        {
            "_id": run_id,
            "source": source,
            "source_ref": source_ref,
            "status": "running",
            "started_at": now(),
        }
    )
    return run_id
