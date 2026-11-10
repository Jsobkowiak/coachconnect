"""Additional free in-app illustrations, original files and per-asset attribution."""

import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from uuid import uuid4

import httpx
from PIL import Image

from exercise_catalog.config import SOURCE_NAME, settings
from exercise_catalog.media import MAX_BYTES, queue_matches
from exercise_catalog.review import fingerprint
from exercise_catalog.store import acquire_lock, connect, initialize, now, start_run

REPDB_REF = "be983c86ff56090900abae35fb51ee83b3e73ac3"
REPDB_ROOT = f"https://raw.githubusercontent.com/RepDB/exercise-dataset/{REPDB_REF}/"
REPDB_LICENSE = {
    "name": "RepDB Free Tier v1.0",
    "url": REPDB_ROOT + "LICENSE-DATA.md",
    "author": "Exercise data by RepDB (repdb.co)",
    "source_url": "https://repdb.co",
    "modified": False,
    "in_app_only": True,
    "ai_generated": True,
}
FORMATS = {
    "PNG": ("png", "image/png"),
    "JPEG": ("jpg", "image/jpeg"),
    "WEBP": ("webp", "image/webp"),
}


def validate_image(payload):
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Image exceeds the size limit")
    with Image.open(io.BytesIO(payload)) as image:
        if image.format not in FORMATS or getattr(image, "is_animated", False):
            raise ValueError("Unsupported illustration format")
        if not all(1 <= dimension <= 4096 for dimension in image.size):
            raise ValueError("Image dimensions exceed the limit")
        width, height = image.size
        extension, mime = FORMATS[image.format]
        image.verify()
    return extension, mime, width, height


def download_bytes(client, url, max_bytes=MAX_BYTES):
    payload = bytearray()
    with client.stream("GET", url) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            payload.extend(chunk)
            if len(payload) > max_bytes:
                raise ValueError("Source download exceeds the size limit")
    return bytes(payload)


def wger_snapshot(client):
    snapshot = {}
    for endpoint in ["exerciseinfo", "license"]:
        url = f"https://wger.de/api/v2/{endpoint}/?limit=1000"
        rows = []
        while url:
            if not url.startswith(f"https://wger.de/api/v2/{endpoint}/?"):
                raise ValueError("Unexpected pagination URL")
            page = json.loads(download_bytes(client, url, 20_000_000))
            rows.extend(page["results"])
            url = page.get("next")
        snapshot[endpoint] = rows
    return snapshot


def source_rows(source, client):
    if source == "repdb":
        payload = download_bytes(client, REPDB_ROOT + "exercises.json", 10_000_000)
        dataset = json.loads(payload)
        rows = []
        for exercise in dataset["exercises"]:
            images = []
            for path in exercise.get("images", {}).get("flat", {}).values():
                if not re.fullmatch(r"images/flat/[a-z0-9-]+\.webp", path):
                    raise ValueError("Unexpected RepDB free image path")
                if path not in [image["path"] for image in images]:
                    images.append(
                        {"path": path, "url": REPDB_ROOT + path, "license": REPDB_LICENSE}
                    )
            rows.append(
                {
                    "id": exercise["id"],
                    "title": exercise["name_en"],
                    "png": images,
                    "payload": exercise,
                    "license": REPDB_LICENSE,
                }
            )
        license_payload = download_bytes(client, REPDB_LICENSE["url"])
        return rows, REPDB_REF, payload, license_payload
    if source != "wger":
        raise ValueError("Unknown illustration source")
    snapshot = wger_snapshot(client)
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
    source_ref = hashlib.sha256(payload).hexdigest()
    licenses = {row["id"]: row for row in snapshot["license"]}
    rows = []
    for exercise in snapshot["exerciseinfo"]:
        english = [t for t in exercise["translations"] if t["language"] == 2]
        if not english:
            continue
        images = []
        for image in exercise["images"]:
            license_record = licenses.get(image["license"])
            if not license_record or image["license"] not in {1, 2, 3, 4}:
                continue
            url = image["image"]
            if not re.fullmatch(r"https://wger\.de/media/exercise-images/[a-zA-Z0-9_./%-]+", url):
                continue
            if not url.lower().endswith((".png", ".jpg", ".jpeg", ".jfif", ".webp")):
                continue
            author = image.get("license_author") or ", ".join(image.get("author_history", []))
            license_data = {
                "name": license_record["short_name"],
                "url": license_record["url"],
                "author": author or "wger — contributeurs",
                "source_url": f"https://wger.de/api/v2/exerciseinfo/{exercise['id']}/",
                "original_url": url,
                "modified": False,
                "title": image.get("license_title") or english[0]["name"],
                "author_url": image.get("license_author_url", ""),
                "derivative_source_url": image.get("license_derivative_source_url", ""),
                "object_url": image.get("license_object_url", ""),
                "ai_generated": image.get("is_ai_generated", False),
            }
            images.append({"path": str(image["uuid"]), "url": url, "license": license_data})
        rows.append(
            {
                "id": str(exercise["id"]),
                "title": english[0]["name"],
                "png": images,
                "payload": exercise,
                "license": images[0]["license"] if images else {},
            }
        )
    return rows, source_ref, payload, json.dumps(snapshot["license"]).encode()


def extract_source(db, config, source):
    with httpx.Client(timeout=45) as client:
        rows, source_ref, payload, license_payload = source_rows(source, client)
        digest = hashlib.sha256(payload).hexdigest()
        folder = config.raw_directory / source / source_ref
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (digest + ".json")).write_bytes(payload)
        (folder / "LICENSE-source.txt").write_bytes(license_payload)
        config.media_directory.mkdir(parents=True, exist_ok=True)
        jobs = {
            (item["url"], json.dumps(item["license"], sort_keys=True)): item
            for row in rows
            for item in row["png"]
        }

        def download(job):
            item = jobs[job]
            key = fingerprint([source, source_ref, item["url"]])
            cached = db.media_assets.find_one({"_id": key})
            if cached and re.fullmatch(r"[a-f0-9]{64}\.(png|jpg|webp)", cached["filename"]):
                local = config.media_directory / cached["filename"]
                if (
                    local.is_file()
                    and hashlib.sha256(local.read_bytes()).hexdigest() == cached["sha256"]
                ):
                    return job, cached
            try:
                image = download_bytes(client, item["url"])
                extension, mime, width, height = validate_image(image)
                sha = hashlib.sha256(image).hexdigest()
                filename = sha + "." + extension
                temporary = config.media_directory / (filename + "." + uuid4().hex + ".tmp")
                temporary.write_bytes(image)
                temporary.replace(config.media_directory / filename)
                asset = {
                    "_id": key,
                    "filename": filename,
                    "sha256": sha,
                    "width": width,
                    "height": height,
                    "mime_type": mime,
                    "url": "/media/assets/" + filename,
                    "source": source,
                    "source_url": item["url"],
                    "source_ref": source_ref,
                    "license": item["license"],
                    "created_at": now(),
                }
                db.media_assets.replace_one({"_id": key}, asset, upsert=True)
                return job, asset
            except (ValueError, OSError, httpx.HTTPError) as error:
                db.media_asset_errors.update_one(
                    {"_id": key},
                    {
                        "$set": {
                            "source": source,
                            "source_ref": source_ref,
                            "url": item["url"],
                            "error_type": type(error).__name__,
                            "last_seen_at": now(),
                        }
                    },
                    upsert=True,
                )
                return job, None

        with ThreadPoolExecutor(max_workers=6) as pool:
            assets = dict(pool.map(download, jobs))
    exclusions_file = files("exercise_catalog").joinpath(
        "data/" + source + "-media-exclusions.json"
    )
    exclusions = (
        json.loads(exclusions_file.read_text()) if exclusions_file.is_file() else {"issues": []}
    )
    blocked = (
        {issue["source_id"]: issue["note"] for issue in exclusions["issues"]}
        if exclusions.get("source_ref") == source_ref
        else {}
    )
    for row in rows:
        images = []
        for item in row["png"]:
            asset = assets[(item["url"], json.dumps(item["license"], sort_keys=True))]
            if asset:
                images.append(
                    {
                        k: asset[k]
                        for k in [
                            "url",
                            "filename",
                            "sha256",
                            "width",
                            "height",
                            "source_url",
                            "license",
                            "mime_type",
                        ]
                    }
                )
        row["png"] = [] if row["id"] in blocked else images
        db.media_sources.replace_one(
            {"_id": f"{source}:{source_ref}:{row['id']}"},
            {
                "_id": f"{source}:{source_ref}:{row['id']}",
                "source": source,
                "source_id": row["id"],
                "source_ref": source_ref,
                "dataset_sha256": digest,
                "title": row["title"],
                "payload": row["payload"],
                "images": images,
                "license": row["license"],
                "quality_status": "blocked" if row["id"] in blocked else "available",
                "quality_note": blocked.get(row["id"]),
            },
            upsert=True,
        )
    return rows, source_ref, digest


def import_additional_media(source):
    config = settings()
    client, db = connect(config)
    run_id = start_run(db, source, REPDB_REF if source == "repdb" else "live-snapshot")
    locked = False
    try:
        initialize(db)
        acquire_lock(db, SOURCE_NAME, run_id)
        locked = True
        rows, source_ref, digest = extract_source(db, config, source)
        manifest_file = files("exercise_catalog").joinpath("data/" + source + "-links.json")
        manifest = (
            json.loads(manifest_file.read_text())
            if manifest_file.is_file()
            else {"links": [], "source_ref": source_ref}
        )
        summary = {
            "total": len(rows),
            "illustrated_sources": sum(bool(r["png"]) for r in rows),
            **queue_matches(db, rows, source, source_ref, manifest),
        }
        db.import_runs.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "status": "completed",
                    "finished_at": now(),
                    "source_ref": source_ref,
                    "summary": summary,
                    "provenance": {"source_ref": source_ref, "sha256": digest},
                }
            },
        )
        return {"run_id": run_id, **summary}
    except Exception as error:
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
