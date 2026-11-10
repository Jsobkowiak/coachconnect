from collections import Counter
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from exercise_catalog.config import SOURCE_NAME
from exercise_catalog.models import normalized_name
from exercise_catalog.quality import duplicate_candidates
from exercise_catalog.review import fingerprint, resolve_review
from exercise_catalog.sources.free_exercise_db import transform
from exercise_catalog.store import now, stable_id


def record_issue(
    db,
    run_id,
    source_key,
    kind,
    message,
    record_hash,
    *,
    severity="error",
    candidates=None,
    raw_id=None,
    signature=None,
):
    issue_id = str(uuid5(NAMESPACE_URL, f"{source_key}:{kind}:{record_hash}"))
    db.quality_issues.update_one(
        {"_id": issue_id},
        {
            "$set": {
                "last_seen_run": run_id,
                "last_seen_at": now(),
                "message": message,
                "candidate_ids": candidates or [],
                "raw_id": raw_id,
                "decision_signature": signature,
            },
            "$setOnInsert": {
                "source_key": source_key,
                "kind": kind,
                "severity": severity,
                "status": "open",
                "created_at": now(),
            },
        },
        upsert=True,
    )

    return db.quality_issues.find_one({"_id": issue_id})


def process_records(db, records: list, metadata: dict, run_id: str) -> dict:
    summary = dict(
        total=len(records), added=0, updated=0, unchanged=0, rejected=0, flagged=0, warnings=0
    )
    existing = list(
        db.exercises.find(
            {},
            {"_id": 1, "source_key": 1, "source_data": 1, "normalized_name": 1, "content_hash": 1},
        )
    )
    source_ids = Counter(
        r.get("id") for r in records if isinstance(r, dict) and isinstance(r.get("id"), str)
    )
    for position, record in enumerate(records):
        if position % 100 == 0:
            # Refresh the lease for long imports; never steal another import's lease.
            db.import_locks.update_one(
                {"_id": SOURCE_NAME, "owner": run_id},
                {"$set": {"expires_at": now() + timedelta(minutes=30)}},
            )
        source_id = record.get("id") if isinstance(record, dict) else None
        source_key = f"{SOURCE_NAME}:{source_id or 'invalid-' + str(position)}"
        raw_id = f"{SOURCE_NAME}:{metadata['sha256']}:{position}"
        db.raw_exercises.update_one(
            {"_id": raw_id},
            {
                "$setOnInsert": {
                    "source": SOURCE_NAME,
                    "source_key": source_key,
                    "snapshot_sha256": metadata["sha256"],
                    "position": position,
                    "payload": record,
                    "provenance": metadata,
                    "first_seen_run": run_id,
                    "created_at": now(),
                }
            },
            upsert=True,
        )
        correction = db.quality_reviews.find_one(
            {"source_key": source_key, "action": "correct", "raw_hash": fingerprint(record)}
        )
        applied_reviews = []
        try:
            if not isinstance(record, dict):
                raise ValueError("An exercise must be a JSON object")
            if isinstance(source_id, str) and source_ids[source_id] > 1:
                raise ValueError("Duplicate source ID within the same snapshot")
            data = transform({**record, **correction["patch"]} if correction else record)
            if correction:
                applied_reviews.append(correction)
        except (ValidationError, ValueError, TypeError, AttributeError) as error:
            record_issue(
                db, run_id, source_key, "invalid_record", str(error), raw_id, raw_id=raw_id
            )
            summary["rejected"] += 1
            continue

        exercise_id = stable_id(source_key)
        previous = db.exercises.find_one({"_id": exercise_id})
        if previous and previous.get("overrides"):
            try:
                # A new source version must still be consistent with manual corrections.
                from exercise_catalog.models import ExerciseData

                ExerciseData.model_validate(
                    {**data.model_dump(mode="json"), **previous["overrides"]}
                )
            except ValidationError as error:
                record_issue(
                    db, run_id, source_key, "override_conflict", str(error), raw_id, raw_id=raw_id
                )
                summary["rejected"] += 1
                continue
        if (
            previous is None
            or previous["content_hash"] != data.content_hash()
            or previous.get("duplicate_reviewed")
        ):
            matches = duplicate_candidates(data, source_key, existing)
            if matches:
                signature = fingerprint(
                    {
                        "content": data.content_hash(),
                        "candidates": sorted(
                            (item["_id"], item["content_hash"])
                            for item in existing
                            if item["_id"] in matches
                        ),
                    }
                )
                issue = record_issue(
                    db,
                    run_id,
                    source_key,
                    "possible_duplicate",
                    "Review this exercise against candidate exercises before publishing",
                    signature,
                    candidates=matches,
                    raw_id=raw_id,
                    signature=signature,
                )
                decision = db.quality_reviews.find_one(
                    {
                        "_id": issue["_id"],
                        "action": "distinct",
                        "decision_signature": signature,
                    }
                )
                if decision is None:
                    summary["flagged"] += 1
                    continue
                applied_reviews.append(decision)

        effective_equipment = {
            **data.model_dump(mode="json"),
            **(previous or {}).get("overrides", {}),
        }["equipment"]
        if effective_equipment is None:
            warning = record_issue(
                db,
                run_id,
                source_key,
                "missing_equipment",
                "The source does not specify the equipment",
                data.content_hash(),
                severity="warning",
                raw_id=raw_id,
            )
            if warning["status"] == "open":
                summary["warnings"] += 1

        def finalize_review(
            applied_reviews=applied_reviews,
            source_key=source_key,
            effective_equipment=effective_equipment,
        ):
            for review in applied_reviews:
                resolve_review(db, review, run_id)
            if effective_equipment is not None:
                db.quality_issues.update_many(
                    {"source_key": source_key, "kind": "missing_equipment", "status": "open"},
                    {
                        "$set": {
                            "status": "resolved",
                            "resolved_at": now(),
                            "resolution": "equipment_corrected",
                            "resolved_run": run_id,
                        }
                    },
                )
            db.quality_issues.update_many(
                {
                    "source_key": source_key,
                    "status": "open",
                    "kind": {"$in": ["invalid_record", "override_conflict", "possible_duplicate"]},
                },
                {
                    "$set": {
                        "status": "resolved",
                        "resolved_at": now(),
                        "resolution": "source_validated",
                        "resolved_run": run_id,
                    }
                },
            )

        source_data = data.model_dump(mode="json")
        content_hash = data.content_hash()
        if previous and previous["content_hash"] == content_hash:
            summary["unchanged"] += 1
            db.exercises.update_one(
                {"_id": exercise_id},
                {
                    "$set": {
                        "last_seen_run": run_id,
                        "last_seen_at": now(),
                        "provenance": metadata,
                        "duplicate_reviewed": any(
                            r["action"] == "distinct" for r in applied_reviews
                        ),
                    }
                },
            )
            finalize_review()
            continue
        db.exercises.update_one(
            {"_id": exercise_id},
            {
                "$set": {
                    "source_data": source_data,
                    "duplicate_reviewed": any(r["action"] == "distinct" for r in applied_reviews),
                    "normalized_name": normalized_name(data.name),
                    "content_hash": content_hash,
                    "provenance": metadata,
                    "updated_at": now(),
                    "last_seen_at": now(),
                    "last_seen_run": run_id,
                },
                "$setOnInsert": {"source_key": source_key, "created_at": now(), "overrides": {}},
            },
            upsert=True,
        )
        finalize_review()
        summary["updated" if previous else "added"] += 1
        view = {
            "_id": exercise_id,
            "source_key": source_key,
            "source_data": source_data,
            "normalized_name": normalized_name(data.name),
            "content_hash": content_hash,
        }
        existing = [item for item in existing if item["_id"] != exercise_id]
        existing.append(view)
    return summary
