"""Local quality decisions, bound to the exact source content under review."""

import hashlib
import json
from uuid import uuid4

from exercise_catalog.config import SOURCE_NAME
from exercise_catalog.sources.free_exercise_db import transform
from exercise_catalog.store import acquire_lock, now


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def inspect_issue(db, issue_id):
    issue = db.quality_issues.find_one({"_id": issue_id})
    if issue is None:
        raise ValueError("Unknown quality issue")
    raw = db.raw_exercises.find_one({"_id": issue.get("raw_id")}) if issue.get("raw_id") else None
    if raw is None:
        raw = db.raw_exercises.find_one(
            {"source_key": issue["source_key"]}, sort=[("created_at", -1)]
        )
    candidates = list(db.exercises.find({"_id": {"$in": issue.get("candidate_ids", [])}}))
    return {"issue": issue, "raw": raw, "candidates": candidates}


def decide(db, issue_id, action, reviewer, note, patch=None):
    if not reviewer.strip() or not note.strip():
        raise ValueError("Reviewer and reason are required")
    if action not in {"correct", "distinct", "acknowledge"}:
        raise ValueError("Unknown decision")
    owner = "review-" + str(uuid4())
    acquire_lock(db, SOURCE_NAME, owner)
    try:
        context = inspect_issue(db, issue_id)
        issue, raw = context["issue"], context["raw"]
        if issue["status"] != "open":
            raise ValueError("This issue is already resolved")
        if db.quality_reviews.find_one({"_id": issue_id}):
            raise ValueError("A decision already exists; run the import to apply it")
        if raw is None:
            raise ValueError("Source snapshot unavailable")
        if action == "correct":
            if issue["kind"] != "invalid_record":
                raise ValueError("Corrections here apply to rejected source records")
            allowed = {
                "name",
                "category",
                "equipment",
                "primaryMuscles",
                "secondaryMuscles",
                "instructions",
                "level",
                "force",
                "mechanic",
            }
            if not isinstance(patch, dict) or not patch or set(patch) - allowed:
                raise ValueError("Provide known source fields; source ID cannot be changed")
            transform({**raw["payload"], **patch})
        elif action == "distinct":
            if issue["kind"] != "possible_duplicate" or not issue.get("decision_signature"):
                raise ValueError("Run an import first to fingerprint the duplicate candidates")
        elif issue["severity"] != "warning":
            raise ValueError("Only warnings can be acknowledged")
        decision = {
            "_id": issue_id,
            "source_key": issue["source_key"],
            "action": action,
            "reviewer": reviewer.strip(),
            "note": note.strip(),
            "created_at": now(),
            "raw_hash": fingerprint(raw["payload"]),
            "patch": patch or {},
            "decision_signature": issue.get("decision_signature"),
        }
        db.quality_reviews.insert_one(decision)
        if action == "acknowledge":
            db.quality_issues.update_one(
                {"_id": issue_id},
                {
                    "$set": {
                        "status": "resolved",
                        "resolved_at": now(),
                        "resolution": "acknowledged",
                        "review_id": issue_id,
                    }
                },
            )
        return decision
    finally:
        db.import_locks.delete_one({"_id": SOURCE_NAME, "owner": owner})


def resolve_review(db, review, run_id):
    db.quality_issues.update_one(
        {"_id": review["_id"]},
        {
            "$set": {
                "status": "resolved",
                "resolved_at": now(),
                "resolution": review["action"],
                "review_id": review["_id"],
                "resolved_run": run_id,
            }
        },
    )
