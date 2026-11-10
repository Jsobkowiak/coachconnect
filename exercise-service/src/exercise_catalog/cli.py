import argparse
import json

from exercise_catalog.config import DEFAULT_SOURCE_REF, settings
from exercise_catalog.models import ExerciseData
from exercise_catalog.store import connect, initialize, now


def main():
    parser = argparse.ArgumentParser(description="Exercise catalogue ETL")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("import-french", help="Publish the authored French catalogue")
    importer = subcommands.add_parser("import", help="Run a tracked Prefect import")
    importer.add_argument(
        "--source-ref", default=DEFAULT_SOURCE_REF, help="Immutable Git commit SHA"
    )
    override = subcommands.add_parser(
        "override", help="Apply a manual correction kept across imports"
    )
    override.add_argument("exercise_id")
    override.add_argument(
        "--file", required=True, help="JSON object with corrected exercise fields"
    )
    quality = subcommands.add_parser("quality", help="Inspect and review quality issues locally")
    operations = quality.add_subparsers(dest="operation", required=True)
    listing = operations.add_parser("list")
    listing.add_argument("--status", choices=["open", "resolved"], default="open")
    inspect = operations.add_parser("inspect")
    inspect.add_argument("issue_id")
    decision = operations.add_parser("decide")
    decision.add_argument("issue_id")
    decision.add_argument("action", choices=["correct", "distinct", "acknowledge"])
    decision.add_argument("--reviewer", required=True)
    decision.add_argument("--note", required=True)
    decision.add_argument("--file", help="JSON patch in source format for rejected records")
    media_importer = subcommands.add_parser(
        "import-media", help="Import licensed illustrations and curated associations"
    )
    media_importer.add_argument(
        "--source", choices=["all", "everkinetic", "repdb", "wger"], default="all"
    )
    media = subcommands.add_parser("media", help="Review illustration matching proposals")
    media_commands = media.add_subparsers(dest="operation", required=True)
    media_list = media_commands.add_parser("list")
    media_list.add_argument(
        "--status", choices=["pending", "approved", "rejected"], default="pending"
    )
    media_inspect = media_commands.add_parser("inspect")
    media_inspect.add_argument("match_id")
    media_approve = media_commands.add_parser("approve")
    media_approve.add_argument("match_id")
    media_approve.add_argument("source_id")
    media_approve.add_argument("--reviewer", required=True)
    media_approve.add_argument("--note", required=True)
    media_reject = media_commands.add_parser("reject")
    media_reject.add_argument("match_id")
    media_reject.add_argument("--reviewer", required=True)
    media_reject.add_argument("--note", required=True)
    arguments = parser.parse_args()
    if arguments.command == "import-french":
        from exercise_catalog.editorial import import_french_catalogue

        print(json.dumps(import_french_catalogue(), indent=2, ensure_ascii=False))
        return
    if arguments.command == "import-media":
        from exercise_catalog.media import import_media

        print(json.dumps(import_media(arguments.source), indent=2, default=str))
        return
    if arguments.command == "media":
        from uuid import uuid4

        from exercise_catalog.config import SOURCE_NAME
        from exercise_catalog.media import approve_match, reject_match
        from exercise_catalog.store import acquire_lock

        client, db = connect(settings())
        owner = "media-review-" + uuid4().hex
        locked = False
        try:
            initialize(db)
            if arguments.operation == "list":
                result = list(db.media_matches.find({"status": arguments.status}))
            elif arguments.operation == "inspect":
                match = db.media_matches.find_one({"_id": arguments.match_id})
                if match is None:
                    raise ValueError("Unknown media match")
                sources = list(
                    db.media_sources.find(
                        {
                            "source_ref": match["source_ref"],
                            "source_id": {
                                "$in": [candidate["source_id"] for candidate in match["candidates"]]
                            },
                        }
                    )
                )
                result = {
                    "match": match,
                    "sources": sources,
                    "exercise": db.exercises.find_one({"_id": match["exercise_id"]}),
                }
            else:
                acquire_lock(db, SOURCE_NAME, owner)
                locked = True
                if arguments.operation == "approve":
                    approve_match(
                        db,
                        arguments.match_id,
                        arguments.source_id,
                        arguments.reviewer,
                        arguments.note,
                    )
                    result = {"status": "approved"}
                else:
                    reject_match(db, arguments.match_id, arguments.reviewer, arguments.note)
                    result = {"status": "rejected"}
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        except ValueError as error:
            parser.error(str(error))
        finally:
            if locked:
                db.import_locks.delete_one({"_id": SOURCE_NAME, "owner": owner})
            client.close()
        return
    if arguments.command == "import":
        from exercise_catalog.flows import import_exercises

        print(json.dumps(import_exercises(arguments.source_ref), indent=2))
        return
    from pathlib import Path

    if arguments.command == "quality":
        from exercise_catalog.review import decide, inspect_issue

        client, db = connect(settings())
        try:
            initialize(db)
            if arguments.operation == "list":
                result = list(
                    db.quality_issues.find({"status": arguments.status}).sort("source_key", 1)
                )
            elif arguments.operation == "inspect":
                result = inspect_issue(db, arguments.issue_id)
            else:
                patch = json.loads(Path(arguments.file).read_text()) if arguments.file else None
                result = decide(
                    db,
                    arguments.issue_id,
                    arguments.action,
                    arguments.reviewer,
                    arguments.note,
                    patch,
                )
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        except ValueError as error:
            parser.error(str(error))
        finally:
            client.close()
        return
    changes = json.loads(Path(arguments.file).read_text())
    if not isinstance(changes, dict) or not changes:
        parser.error("The correction must be a non-empty JSON object")
    client, db = connect(settings())
    try:
        initialize(db)
        document = db.exercises.find_one({"_id": arguments.exercise_id})
        if document is None:
            parser.error("Unknown exercise ID")
        combined = {**document["overrides"], **changes}
        ExerciseData.model_validate({**document["source_data"], **combined})
        db.exercises.update_one(
            {"_id": arguments.exercise_id}, {"$set": {"overrides": combined, "corrected_at": now()}}
        )
        print("Correction enregistrée.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
