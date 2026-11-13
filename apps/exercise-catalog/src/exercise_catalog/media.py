"""Versioned media import and explicit, content-bound illustration review."""

import hashlib
import json
import re
import struct
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from importlib.resources import files
from uuid import uuid4

import httpx
from prefect import flow

from exercise_catalog.config import SOURCE_NAME, settings
from exercise_catalog.models import ExerciseData, normalized_name
from exercise_catalog.review import fingerprint
from exercise_catalog.store import acquire_lock, connect, initialize, now, start_run

SOURCE = "everkinetic"
SOURCE_REF = "446bb9a3d0c3beb6b84f7c9d77dfc8af707a2ab6"
ROOT_URL = f"https://raw.githubusercontent.com/everkinetic/data/{SOURCE_REF}/"
LICENSE = {
    "name": "CC BY-SA 4.0",
    "url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "author": "Everkinetic / Greg Priday",
    "source_url": "https://github.com/everkinetic/data",
    "license_source_url": ROOT_URL + "LICENSE.md",
    "modified": False,
}
MAX_BYTES = 2_000_000


def effective_hash(document):
    return ExerciseData.model_validate(
        {**document["source_data"], **document.get("overrides", {})}
    ).content_hash()


def validate_png(payload):
    if len(payload) > MAX_BYTES or len(payload) < 33 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid or oversized PNG image")
    if payload[12:16] != b"IHDR":
        raise ValueError("PNG image must start with IHDR")
    width, height = struct.unpack(">II", payload[16:24])
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        raise ValueError("PNG dimensions exceed the limit")
    return width, height


def fetch_bytes(client, url):
    data = bytearray()
    with client.stream("GET", url) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError("Media source exceeds the download size limit")
    return bytes(data)


def extract_media(db, config):
    folder = config.raw_directory / SOURCE / SOURCE_REF
    folder.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30) as client:
        payload = fetch_bytes(client, ROOT_URL + "dist/exercises.json")
        digest = hashlib.sha256(payload).hexdigest()
        (folder / (digest + ".json")).write_bytes(payload)
        (folder / "LICENSE.md").write_bytes(fetch_bytes(client, ROOT_URL + "LICENSE.md"))
        rows = json.loads(payload)
        if not isinstance(rows, list) or not rows:
            raise ValueError("Invalid media dataset")
        jobs = []
        seen = set()
        for row in rows:
            if not re.fullmatch(r"\d{4}", row.get("id", "")):
                raise ValueError("Invalid illustration source ID")
            for path in row.get("png", []):
                if not re.fullmatch(r"png/[a-z0-9][a-z0-9-]{1,100}\.png", path):
                    raise ValueError("Unsafe source image path")
                if path not in seen:
                    seen.add(path)
                    jobs.append(path)

        config.media_directory.mkdir(parents=True, exist_ok=True)

        def download(path):
            key = fingerprint([SOURCE_REF, path])
            cached = db.media_assets.find_one({"_id": key})
            if cached:
                local = config.media_directory / cached["filename"]
                if (
                    local.exists()
                    and hashlib.sha256(local.read_bytes()).hexdigest() == cached["sha256"]
                ):
                    return cached
            url = ROOT_URL + "dist/" + path
            image = fetch_bytes(client, url)
            width, height = validate_png(image)
            sha = hashlib.sha256(image).hexdigest()
            filename = sha + ".png"
            temporary = config.media_directory / (filename + "." + uuid4().hex + ".tmp")
            temporary.write_bytes(image)
            temporary.replace(config.media_directory / filename)
            asset = {
                "_id": key,
                "filename": filename,
                "sha256": sha,
                "width": width,
                "height": height,
                "url": "/media/assets/" + filename,
                "source_url": url,
                "source_path": path,
                "source_ref": SOURCE_REF,
                "license": LICENSE,
                "created_at": now(),
            }
            db.media_assets.replace_one({"_id": key}, asset, upsert=True)
            return asset

        with ThreadPoolExecutor(max_workers=6) as pool:
            assets = {item["source_path"]: item for item in pool.map(download, jobs)}
    for row in rows:
        images = []
        for path in row.get("png", []):
            asset = assets[path]
            images.append(
                {
                    k: asset[k]
                    for k in ["url", "filename", "sha256", "width", "height", "source_url"]
                }
            )
        db.media_sources.replace_one(
            {"_id": SOURCE + ":" + SOURCE_REF + ":" + row["id"]},
            {
                "_id": SOURCE + ":" + SOURCE_REF + ":" + row["id"],
                "source_id": row["id"],
                "source_ref": SOURCE_REF,
                "dataset_sha256": digest,
                "title": row["title"],
                "payload": row,
                "images": images,
                "license": LICENSE,
            },
            upsert=True,
        )
    return rows, digest


def candidate_sources(name, source_rows):
    # Similarity only suggests candidates. It never authorizes publication.
    ranked = []
    for row in source_rows:
        if not row.get("png"):
            continue
        score = SequenceMatcher(None, normalized_name(name), normalized_name(row["title"])).ratio()
        if score >= 0.72:
            ranked.append({"source_id": row["id"], "title": row["title"], "score": round(score, 3)})
    return sorted(ranked, key=lambda item: (-item["score"], item["source_id"]))[:3]


def queue_matches(db, rows, source=SOURCE, source_ref=SOURCE_REF, manifest=None):
    if manifest is None:
        manifest = json.loads(
            files("exercise_catalog").joinpath("data/" + source + "-links.json").read_text()
        )
    curated = {item["source_key"]: item for item in manifest["links"]}
    counts = {"approved": 0, "pending": 0, "unmatched": 0}
    for document in db.exercises.find():
        target_hash = effective_hash(document)
        data = {**document["source_data"], **document.get("overrides", {})}
        match_id = fingerprint([document["_id"], target_hash, source_ref])
        candidates = candidate_sources(data["name"], rows)
        curated_link = curated.get(document["source_key"])
        valid_curated = (
            curated_link
            and curated_link["target_hash"] == target_hash
            and manifest["source_ref"] == source_ref
        )
        if valid_curated:
            candidates = [
                {
                    "source_id": curated_link["source_id"],
                    "title": curated_link["source_title"],
                    "score": 1.0,
                }
            ]
        if not candidates:
            counts["unmatched"] += 1
            continue
        db.media_matches.update_one(
            {"_id": match_id},
            {
                "$setOnInsert": {
                    "exercise_id": document["_id"],
                    "source_key": document["source_key"],
                    "exercise_name": data["name"],
                    "target_hash": target_hash,
                    "source_ref": source_ref,
                    "source": source,
                    "candidates": candidates,
                    "status": "pending",
                    "created_at": now(),
                },
            },
            upsert=True,
        )
        match = db.media_matches.find_one({"_id": match_id})
        if valid_curated and match["status"] == "pending":
            db.media_matches.update_one(
                {"_id": match_id, "status": "pending"}, {"$set": {"candidates": candidates}}
            )
            approve_match(db, match_id, curated_link["source_id"], "Codex", curated_link["note"])
            match = db.media_matches.find_one({"_id": match_id})
        if match["status"] == "approved":
            publish_match(db, match)
            counts["approved"] += 1
        elif match["status"] == "pending":
            counts["pending"] += 1
    return counts


def publish_match(db, match):
    exercise = db.exercises.find_one({"_id": match["exercise_id"]})
    if exercise is None or effective_hash(exercise) != match["target_hash"]:
        raise ValueError("Exercise content changed; review the new version")
    source = db.media_sources.find_one(
        {"source_ref": match["source_ref"], "source_id": match["source_id"]}
    )
    if source is None or not source["images"] or source.get("quality_status") == "blocked":
        raise ValueError("Illustrations unavailable for this source exercise")
    media = {
        "target_hash": match["target_hash"],
        "review_id": match["_id"],
        "source": source.get("source", SOURCE),
        "source_id": source["source_id"],
        "source_ref": source["source_ref"],
        "title": source["title"],
        "images": source["images"],
        "license": source["license"],
    }
    current = exercise.get("media")
    if (
        current
        and current.get("target_hash") == match["target_hash"]
        and current.get("review_id") != match["_id"]
    ):
        return  # Preserve an existing reviewed illustration from another source.
    db.exercises.update_one({"_id": exercise["_id"]}, {"$set": {"media": media}})


def approve_match(db, match_id, source_id, reviewer, note):
    if not reviewer.strip() or not note.strip():
        raise ValueError("Reviewer and reason are required")
    match = db.media_matches.find_one({"_id": match_id})
    if not match or match["status"] != "pending":
        raise ValueError("Unknown or already reviewed media match")
    if source_id not in {candidate["source_id"] for candidate in match["candidates"]}:
        raise ValueError("Choose one of the proposed source IDs")
    proposal = {**match, "source_id": source_id}
    # Verify both sides before recording the decision; failed reviews stay pending.
    exercise = db.exercises.find_one({"_id": match["exercise_id"]})
    source = db.media_sources.find_one({"source_ref": match["source_ref"], "source_id": source_id})
    if not exercise or effective_hash(exercise) != match["target_hash"]:
        raise ValueError("Exercise content changed; review the new version")
    if not source or not source["images"] or source.get("quality_status") == "blocked":
        raise ValueError("Source exercise has no available images")
    result = db.media_matches.update_one(
        {"_id": match_id, "status": "pending"},
        {
            "$set": {
                "status": "approved",
                "source_id": source_id,
                "reviewer": reviewer.strip(),
                "note": note.strip(),
                "reviewed_at": now(),
            }
        },
    )
    if result.modified_count != 1:
        raise ValueError("Media match was reviewed concurrently")
    publish_match(db, proposal)


def reject_match(db, match_id, reviewer, note):
    if not reviewer.strip() or not note.strip():
        raise ValueError("Reviewer and reason are required")
    result = db.media_matches.update_one(
        {"_id": match_id, "status": "pending"},
        {
            "$set": {
                "status": "rejected",
                "reviewer": reviewer.strip(),
                "note": note.strip(),
                "reviewed_at": now(),
            }
        },
    )
    if result.modified_count != 1:
        raise ValueError("Unknown or already reviewed media match")


@flow(name="import-exercise-illustrations", persist_result=False, log_prints=True)
def import_media(source="all"):
    if source != SOURCE:
        from exercise_catalog.media_sources import import_additional_media

        if source == "all":
            return {
                SOURCE: import_media(SOURCE),
                "repdb": import_additional_media("repdb"),
                "wger": import_additional_media("wger"),
            }
        return import_additional_media(source)
    config = settings()
    client, db = connect(config)
    run_id = None
    locked = False
    try:
        initialize(db)
        run_id = start_run(db, SOURCE, SOURCE_REF)
        acquire_lock(db, SOURCE_NAME, run_id)
        locked = True
        rows, digest = extract_media(db, config)
        summary = {
            "total": len(rows),
            "illustrated_sources": sum(bool(row["png"]) for row in rows),
            **queue_matches(db, rows),
        }
        db.import_runs.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "status": "completed",
                    "finished_at": now(),
                    "summary": summary,
                    "provenance": {
                        "source_ref": SOURCE_REF,
                        "sha256": digest,
                        "license": LICENSE,
                        "url": ROOT_URL + "dist/exercises.json",
                    },
                }
            },
        )
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
