from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE

from exercise_catalog.config import DEFAULT_SOURCE_REF, SOURCE_NAME, settings
from exercise_catalog.pipeline import process_records
from exercise_catalog.sources.free_exercise_db import extract
from exercise_catalog.store import acquire_lock, connect, initialize, now, start_run


@task(
    name="extract-free-exercise-db",
    retries=3,
    retry_delay_seconds=5,
    cache_policy=NO_CACHE,
    persist_result=False,
)
def extract_source(source_ref: str):
    return extract(source_ref, settings().raw_directory)


@task(name="validate-and-load", cache_policy=NO_CACHE, persist_result=False)
def validate_and_load(records: list, metadata: dict, run_id: str):
    client, db = connect(settings())
    try:
        return process_records(db, records, metadata, run_id)
    finally:
        client.close()


@flow(name="import-exercise-catalogue", persist_result=False, log_prints=True)
def import_exercises(source_ref: str = DEFAULT_SOURCE_REF) -> dict:
    client, db = connect(settings())
    run_id = None
    locked = False
    try:
        initialize(db)
        run_id = start_run(db, SOURCE_NAME, source_ref)
        acquire_lock(db, SOURCE_NAME, run_id)
        locked = True
        records, metadata = extract_source(source_ref)
        db.import_runs.update_one({"_id": run_id}, {"$set": {"provenance": metadata}})
        summary = validate_and_load(records, metadata, run_id)
        db.import_runs.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "status": "completed",
                    "finished_at": now(),
                    "summary": summary,
                }
            },
        )
        get_run_logger().info("Import finished: %s", summary)
        return {"run_id": run_id, **summary}
    except Exception as error:
        if run_id:
            db.import_runs.update_one(
                {"_id": run_id},
                {
                    "$set": {
                        "status": "failed",
                        "finished_at": now(),
                        "error_type": type(error).__name__,
                    }
                },
            )
        raise
    finally:
        if locked:
            db.import_locks.delete_one({"_id": SOURCE_NAME, "owner": run_id})
        client.close()
