import os
from uuid import uuid4

import pytest

from exercise_catalog.config import Settings
from exercise_catalog.store import connect, initialize


@pytest.fixture
def record():
    return {
        "id": "Barbell_Squat",
        "name": "Barbell Squat",
        "equipment": "barbell",
        "category": "strength",
        "primaryMuscles": ["quadriceps"],
        "secondaryMuscles": ["glutes"],
        "instructions": ["Stand with the bar on your back."],
        "level": "intermediate",
        "force": "push",
        "mechanic": "compound",
    }


@pytest.fixture
def metadata():
    return {
        "sha256": "a" * 64,
        "source_ref": "b" * 40,
        "url": "https://example.test/exercises.json",
        "license": "test-only",
    }


@pytest.fixture
def database():
    uri = os.environ.get("CATALOG_TEST_MONGO_URI")
    if not uri:
        pytest.skip("Set CATALOG_TEST_MONGO_URI to run MongoDB integration tests")
    config = Settings(mongo_uri=uri, database="coachconnect_test_" + uuid4().hex)
    client, db = connect(config)
    initialize(db)
    try:
        yield db, config
    finally:
        client.drop_database(config.database)
        client.close()
