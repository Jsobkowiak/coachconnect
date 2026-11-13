import pytest

from exercise_catalog.config import SOURCE_NAME
from exercise_catalog.pipeline import process_records
from exercise_catalog.review import decide
from exercise_catalog.store import stable_id

pytestmark = pytest.mark.integration


def test_rejected_correction_is_scoped_to_raw_content(database, record, metadata):
    db, _ = database
    bad = {**record, "secondaryMuscles": ["quadriceps", "glutes"]}
    process_records(db, [bad], metadata, "first")
    issue = db.quality_issues.find_one()
    decide(
        db,
        issue["_id"],
        "correct",
        "Jonathan",
        "Keep source primary classification",
        {"secondaryMuscles": ["glutes"]},
    )
    assert db.quality_issues.find_one()["status"] == "open"
    result = process_records(db, [bad], metadata, "apply")
    assert result["added"] == 1
    assert db.quality_issues.find_one()["status"] == "resolved"
    assert db.raw_exercises.find_one()["payload"] == bad
    assert process_records(db, [bad], metadata, "replay")["unchanged"] == 1
    changed = {**bad, "instructions": ["Changed upstream."]}
    result = process_records(db, [changed], {**metadata, "sha256": "c" * 64}, "new-source")
    assert result["rejected"] == 1
    assert db.quality_issues.count_documents({"status": "open"}) == 1
    assert db.exercises.find_one()["source_data"]["instructions"] == record["instructions"]


def test_distinct_decision_replay_and_candidate_change(database, record, metadata):
    db, _ = database
    variant = {**record, "id": "Squat_variant", "name": "Barbell Squats"}
    process_records(db, [record, variant], metadata, "first")
    issue = db.quality_issues.find_one({"kind": "possible_duplicate"})
    decide(db, issue["_id"], "distinct", "Jonathan", "Distinct variant reviewed")
    assert process_records(db, [record, variant], metadata, "apply")["added"] == 1
    replay = process_records(db, [record, variant], metadata, "replay")
    assert replay["unchanged"] == 2
    assert replay["flagged"] == 0
    # Updating a candidate invalidates the previous approval even if the variant is unchanged.
    candidate_id = stable_id(f"{SOURCE_NAME}:{record['id']}")
    db.exercises.update_one({"_id": candidate_id}, {"$set": {"content_hash": "changed"}})
    result = process_records(db, [variant], metadata, "candidate-changed")
    assert result["flagged"] == 1
    assert db.quality_issues.count_documents({"status": "open"}) == 1


def test_warning_acknowledgement_and_guardrails(database, record, metadata):
    db, _ = database
    missing = {**record, "equipment": None}
    process_records(db, [missing], metadata, "first")
    issue = db.quality_issues.find_one()
    with pytest.raises(ValueError, match="required"):
        decide(db, issue["_id"], "acknowledge", "", "reason")
    with pytest.raises(ValueError, match="duplicate"):
        decide(db, issue["_id"], "distinct", "Jonathan", "reason")
    decide(db, issue["_id"], "acknowledge", "Jonathan", "Source does not specify equipment")
    assert process_records(db, [missing], metadata, "replay")["warnings"] == 0
    assert db.quality_reviews.count_documents({}) == 1


def test_correction_validation_and_identity_are_protected(database, record, metadata):
    db, _ = database
    bad = {**record, "instructions": []}
    process_records(db, [bad], metadata, "first")
    issue = db.quality_issues.find_one()
    with pytest.raises(ValueError):
        decide(db, issue["_id"], "correct", "Jonathan", "reason", {"instructions": []})
    with pytest.raises(ValueError, match="ID"):
        decide(db, issue["_id"], "correct", "Jonathan", "reason", {"id": "replacement"})
    assert db.quality_reviews.count_documents({}) == 0
    assert db.import_locks.count_documents({}) == 0


def test_corrected_equipment_closes_stale_warning(database, record, metadata):
    db, _ = database
    missing = {**record, "equipment": None}
    process_records(db, [missing], metadata, "first")
    db.exercises.update_one({}, {"$set": {"overrides.equipment": "barbell"}})
    replay = process_records(db, [missing], metadata, "corrected")
    assert replay["warnings"] == 0
    issue = db.quality_issues.find_one()
    assert issue["status"] == "resolved"
    assert issue["resolution"] == "equipment_corrected"
