import pytest
from pymongo.errors import WriteError

from exercise_catalog.config import SOURCE_NAME
from exercise_catalog.pipeline import process_records
from exercise_catalog.store import acquire_lock, stable_id

pytestmark = pytest.mark.integration


def test_replay_updates_and_manual_corrections(database, record, metadata):
    db, _ = database
    first = process_records(db, [record], metadata, "first")
    exercise_id = stable_id(f"{SOURCE_NAME}:{record['id']}")
    assert first["added"] == 1
    replay = process_records(db, [record], metadata, "replay")
    assert replay["unchanged"] == 1
    assert db.exercises.count_documents({}) == 1
    assert db.raw_exercises.count_documents({}) == 1
    db.exercises.update_one({"_id": exercise_id}, {"$set": {"overrides.name": "Mon squat"}})
    newer = {**record, "instructions": ["An updated instruction."]}
    updated = process_records(db, [newer], {**metadata, "sha256": "c" * 64}, "update")
    assert updated["updated"] == 1
    document = db.exercises.find_one({"_id": exercise_id})
    assert document["overrides"]["name"] == "Mon squat"
    assert document["source_data"]["instructions"] == ["An updated instruction."]
    assert db.raw_exercises.count_documents({}) == 2


def test_rejections_duplicates_and_warnings(database, record, metadata):
    db, _ = database
    rows = [
        record,
        {**record, "id": "Duplicate_Squat"},
        {**record, "id": "Bad_Muscles", "primaryMuscles": ["invented"]},
        {**record, "id": "No_Equipment", "name": "Other movement", "equipment": None},
        None,
    ]
    result = process_records(db, rows, metadata, "test")
    assert result == dict(
        total=5, added=2, updated=0, unchanged=0, rejected=2, flagged=1, warnings=1
    )
    assert db.exercises.count_documents({}) == 2
    assert db.quality_issues.count_documents({"kind": "possible_duplicate"}) == 1
    assert db.quality_issues.count_documents({"severity": "warning"}) == 1
    process_records(db, rows, metadata, "replay")
    assert db.quality_issues.count_documents({}) == 4
    assert db.raw_exercises.count_documents({}) == 5


def test_duplicate_source_ids_are_both_rejected(database, record, metadata):
    db, _ = database
    result = process_records(db, [record, record], metadata, "test")
    assert result["rejected"] == 2
    assert db.exercises.count_documents({}) == 0


def test_invalid_update_keeps_last_good_version(database, record, metadata):
    db, _ = database
    process_records(db, [record], metadata, "first")
    process_records(db, [{**record, "name": ""}], {**metadata, "sha256": "d" * 64}, "bad")
    assert db.exercises.find_one()["source_data"]["name"] == record["name"]


def test_database_validation_and_import_lock(database):
    db, _ = database
    with pytest.raises(WriteError):
        db.exercises.insert_one({"_id": "invalid"})
    acquire_lock(db, SOURCE_NAME, "owner")
    with pytest.raises(RuntimeError, match="already running"):
        acquire_lock(db, SOURCE_NAME, "other-owner")
    assert db.import_locks.find_one()["owner"] == "owner"
