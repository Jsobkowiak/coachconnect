import hashlib
import json
import re
from pathlib import Path

import httpx

from exercise_catalog.models import ExerciseData

REPOSITORY = "https://github.com/yuhonas/free-exercise-db"
LICENSE = "Unlicense (declared by source)"
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


def extract(source_ref: str, raw_directory: Path) -> tuple[list, dict]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("source_ref must be an immutable Git commit SHA")
    url = f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/{source_ref}/dist/exercises.json"
    payload = bytearray()
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                payload.extend(chunk)
                if len(payload) > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Source download exceeds the size limit")
    digest = hashlib.sha256(payload).hexdigest()
    folder = raw_directory / source_ref
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest}.json"
    if not path.exists():
        temporary = folder / f"{digest}.tmp"
        temporary.write_bytes(payload)
        temporary.replace(path)
    records = json.loads(payload)
    if not isinstance(records, list) or not records:
        raise ValueError("Source must contain a non-empty JSON array")
    return records, {
        "url": url,
        "repository": REPOSITORY,
        "source_ref": source_ref,
        "sha256": digest,
        "snapshot": str(path),
        "license": LICENSE,
        "license_url": f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/{source_ref}/LICENSE.md",
    }


def transform(record: dict) -> ExerciseData:
    source_id = record.get("id")
    if not isinstance(source_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", source_id):
        raise ValueError("Missing or invalid source exercise id")
    equipment = record.get("equipment")
    if equipment == "body only":
        equipment = "bodyweight"
    elif isinstance(equipment, str):
        equipment = equipment.replace(" ", "_").replace("-", "")
    # Keep absent values absent; do not invent equipment or muscle information.
    return ExerciseData.model_validate(
        {
            "name": record.get("name"),
            "category": str(record.get("category", "")).replace(" ", "_"),
            "equipment": equipment,
            "primary_muscles": [m.replace(" ", "_") for m in record.get("primaryMuscles", [])],
            "secondary_muscles": [m.replace(" ", "_") for m in record.get("secondaryMuscles", [])],
            "instructions": record.get("instructions"),
            "level": record.get("level"),
            "force": record.get("force"),
            "mechanic": record.get("mechanic"),
        }
    )
