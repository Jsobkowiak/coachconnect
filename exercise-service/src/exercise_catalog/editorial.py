"""Versioned, authored French catalogue independent of external source imports."""

import hashlib
import json
import re
from datetime import date
from typing import Annotated
from io import BytesIO

from PIL import Image
from importlib.resources import files
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from exercise_catalog.config import SOURCE_NAME, settings
from exercise_catalog.media import effective_hash
from exercise_catalog.models import ExerciseData, normalized_name
from exercise_catalog.review import fingerprint
from exercise_catalog.store import acquire_lock, connect, initialize, now, stable_id, start_run


class FrenchExercise(ExerciseData):
    description: str = Field(min_length=10, max_length=500)
    common_mistakes: list[str] = Field(min_length=1, max_length=8)
    required_equipment: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def french_content(self):
        if self.language != "fr" or len(self.instructions) < 3:
            raise ValueError("French catalogue entries require French and at least three steps")
        for value in self.common_mistakes + self.required_equipment:
            if not value.strip():
                raise ValueError("Empty editorial guidance")
        return self


class EditorialEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,100}$")
    data: FrenchExercise
    authored_on: date | None = None
    reference_key: str | None = None
    reference_hash: str | None = None
    diagram: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}\.svg$")
    illustrations: list[Annotated[str, Field(pattern=r"^[a-f0-9]{64}\.(png|webp)$")]] = Field(default_factory=list, max_length=4)
    media_source: str | None = None
    media_source_ref: str | None = None
    media_note: str = Field(min_length=10)
    references: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def complete_reference(self):
        if bool(self.reference_key) != bool(self.reference_hash):
            raise ValueError("Reference and its content hash are required together")
        if bool(self.media_source) != bool(self.media_source_ref):
            raise ValueError("Media source and its version are required together")
        # Source references preserve identity and provenance even when original
        # artwork replaces their media. Only the artwork providers are exclusive.
        if sum(bool(value) for value in [self.media_source, self.diagram, self.illustrations]) > 1:
            raise ValueError("Use only one illustration provider")
        if self.reference_key and (self.media_source or self.diagram):
            raise ValueError("A source reference may only override media with original illustrations")
        return self


def active_documents(db):
    active = db.catalog_settings.find_one({"_id": "active-french-catalogue"})
    if not active:
        return None
    return list(db.curated_exercises.find({"revision": active["revision"]}).sort("data.name", 1))


def editorial_view(document):
    return {
        "id": document["exercise_id"],
        **document["data"],
        "source_key": "coachconnect-fr:" + document["key"],
        "provenance": document["provenance"],
        "media": document.get("media"),
        "updated_at": document["created_at"],
    }


def prepare_entries(db, config, seed):
    entries = [EditorialEntry.model_validate(row) for row in seed["entries"]]
    if not entries or len({row.key for row in entries}) != len(entries):
        raise ValueError("Empty catalogue or duplicate editorial keys")
    if len({normalized_name(row.data.name) for row in entries}) != len(entries):
        raise ValueError("Duplicate French exercise names")
    prepared = []
    for entry in entries:
        media = None
        identifier = stable_id("coachconnect-fr:" + entry.key)
        reference = None
        if entry.reference_key:
            reference = db.exercises.find_one({"source_key": entry.reference_key})
            if not reference or effective_hash(reference) != entry.reference_hash:
                raise ValueError("Reference changed or unavailable: " + entry.key)
            identifier = reference["_id"]  # Existing cycle references remain valid.
            candidate = reference.get("media")
            if candidate and candidate.get("target_hash") == entry.reference_hash:
                media = dict(candidate)
        elif entry.media_source:
            source = db.media_sources.find_one(
                {"source_ref": entry.media_source_ref, "source_id": entry.media_source}
            )
            if not source or source.get("quality_status") == "blocked" or not source["images"]:
                raise ValueError("Reviewed media unavailable: " + entry.key)
            media = {
                "source": source["source"], "source_id": source["source_id"],
                "source_ref": source["source_ref"], "images": source["images"],
                "license": source["license"], "title": entry.data.name,
            }
        if entry.diagram:
            media = {
                "source": "coachconnect", "source_id": entry.key, "source_ref": seed["version"],
                "title": entry.data.name, "images": [{"filename": entry.diagram,
                    "url": "/media/assets/" + entry.diagram}],
                "license": {"name": "CC BY 4.0", "author": "CoachConnect",
                    "url": "https://creativecommons.org/licenses/by/4.0/",
                    "source_url": "http://localhost:8081/", "modified": False},
            }
        if entry.illustrations:
            media = {
                "source": "coachconnect", "source_id": entry.key, "source_ref": seed["version"],
                "title": entry.data.name,
                "images": [{"filename": name, "url": "/media/assets/" + name}
                           for name in entry.illustrations],
                "license": {"name": "Création originale pour CoachConnect",
                    "author": "CoachConnect", "url": "http://localhost:8081/",
                    "source_url": "http://localhost:8081/", "modified": False,
                    "ai_generated": True},
            }
        if media:
            for asset in media["images"]:
                filename = asset["filename"]
                if not re.fullmatch(r"[a-f0-9]{64}\.(png|jpg|webp|svg)", filename):
                    raise ValueError("Invalid asset filename")
                path = (files("exercise_catalog").joinpath("data/diagrams/" + filename)
                        if filename.endswith(".svg") else
                        files("exercise_catalog").joinpath("data/illustrations/" + filename)
                        if entry.illustrations else config.media_directory / filename)
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != filename[:64]:
                    raise ValueError("Missing or corrupted asset: " + entry.key)
                if entry.illustrations:
                    payload = path.read_bytes()
                    if len(payload) > 2_000_000:
                        raise ValueError("Oversized illustration: " + entry.key)
                    with Image.open(BytesIO(payload)) as image:
                        if image.format not in {"PNG", "WEBP"} or not (1 <= image.width <= 4096 and 1 <= image.height <= 4096):
                            raise ValueError("Invalid illustration: " + entry.key)
                        image.verify()
            media.update(
                target_hash=entry.data.content_hash(), title=entry.data.name,
                review_id="editorial:" + seed["version"] + ":" + entry.key,
                review_note=entry.media_note,
            )
        prepared.append({
            "exercise_id": identifier, "key": entry.key,
            "data": entry.data.model_dump(mode="json"), "media": media,
            "reference_key": entry.reference_key, "reference_hash": entry.reference_hash,
            "content_hash": entry.data.content_hash(),
            "provenance": {
                "source": "coachconnect-fr", "version": seed["version"],
                "author": "Codex", "authored_on": (entry.authored_on.isoformat()
                    if entry.authored_on else seed["authored_on"]),
                "review": "Contrôle éditorial du matériel, de la variante et des visuels",
                "references": entry.references, "media_note": entry.media_note,
            },
        })
    if len({row["exercise_id"] for row in prepared}) != len(prepared):
        raise ValueError("Two editorial entries reference the same exercise")
    return prepared


def publish_seed(db, config, seed):
    # Validate the complete batch, references and files before changing the active catalogue.
    prepared = prepare_entries(db, config, seed)
    revision = fingerprint(seed)
    for document in prepared:
        db.curated_exercises.update_one(
            {"_id": revision + ":" + document["exercise_id"]},
            {"$setOnInsert": {**document, "revision": revision, "created_at": now()}}, upsert=True,
        )
    db.catalog_settings.update_one(
        {"_id": "active-french-catalogue"},
        {"$set": {"revision": revision, "version": seed["version"], "activated_at": now()}},
        upsert=True,
    )
    return {"revision": revision, "total": len(prepared),
            "illustrated": sum(bool(row["media"]) for row in prepared), "language": "fr"}


def import_french_catalogue():
    config = settings()
    client, db = connect(config)
    owner = "editorial-" + uuid4().hex
    locked = False
    run_id = None
    try:
        initialize(db)
        acquire_lock(db, SOURCE_NAME, owner)
        locked = True
        seed = json.loads(files("exercise_catalog").joinpath("data/catalogue-fr.json").read_text())
        run_id = start_run(db, "coachconnect-fr", seed["version"])
        summary = publish_seed(db, config, seed)
        db.import_runs.update_one({"_id": run_id}, {"$set": {
            "status": "completed", "summary": summary, "finished_at": now(),
        }})
        return summary
    except Exception as error:
        if run_id:
            db.import_runs.update_one({"_id": run_id}, {"$set": {
                "status": "failed", "error_type": type(error).__name__, "finished_at": now(),
            }})
        raise
    finally:
        if locked:
            db.import_locks.delete_one({"_id": SOURCE_NAME, "owner": owner})
        client.close()
