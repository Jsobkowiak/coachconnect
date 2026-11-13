import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from exercise_catalog import api
from exercise_catalog.media import effective_hash, queue_matches
from exercise_catalog.media_sources import validate_image
from exercise_catalog.pipeline import process_records


@pytest.mark.parametrize(
    "format,extension,mime",
    [("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg"), ("WEBP", "webp", "image/webp")],
)
def test_original_raster_validation(format, extension, mime):
    out = io.BytesIO()
    Image.new("RGB", (12, 8)).save(out, format=format)
    assert validate_image(out.getvalue()) == (extension, mime, 12, 8)
    with pytest.raises((ValueError, OSError)):
        validate_image(b'<svg onload="alert(1)"/>')
    out = io.BytesIO()
    Image.new("RGB", (1, 1)).save(out, format="GIF")
    with pytest.raises(ValueError):
        validate_image(out.getvalue())


@pytest.mark.integration
def test_multisource_reviews_blocking_priority_and_coverage(
    database, record, metadata, monkeypatch, tmp_path
):
    db, config = database
    config.media_directory = tmp_path
    process_records(db, [record], metadata, "initial")
    target = db.exercises.find_one()

    def manifest(ref):
        return {
            "source_ref": ref,
            "links": [
                {
                    "source_key": target["source_key"],
                    "target_hash": effective_hash(target),
                    "source_id": "reviewed",
                    "source_title": "Different wording",
                    "note": "Movement and actual positions verified",
                }
            ],
        }

    rows = [{"id": "reviewed", "title": "Different wording", "png": ["image"]}]
    for source, ref, format, ext in [
        ("everkinetic", "one", "PNG", "png"),
        ("repdb", "two", "WEBP", "webp"),
        ("wger", "three", "JPEG", "jpg"),
    ]:
        # Filename must be a SHA-like hex string for the public route.
        filename = {"one": "a", "two": "b", "three": "c"}[ref] * 64 + "." + ext
        out = io.BytesIO()
        Image.new("RGB", (12, 8)).save(out, format=format)
        (tmp_path / filename).write_bytes(out.getvalue())
        db.media_sources.insert_one(
            {
                "source": source,
                "source_ref": ref,
                "source_id": "reviewed",
                "title": "Different wording",
                "images": [{"filename": filename, "url": "/media/assets/" + filename}],
                "license": {"name": "test"},
                "quality_status": "blocked" if source == "wger" else "available",
            }
        )
        if source == "wger":
            with pytest.raises(ValueError, match="available"):
                queue_matches(db, rows, source, ref, manifest(ref))
            assert db.media_matches.find_one({"source_ref": ref})["status"] == "pending"
        else:
            assert queue_matches(db, rows, source, ref, manifest(ref))["approved"] == 1
            assert queue_matches(db, rows, source, ref, manifest(ref))["approved"] == 1
    assert db.exercises.find_one()["media"]["source"] == "everkinetic"
    monkeypatch.setattr(api, "settings", lambda: config)
    with TestClient(api.app) as client:
        coverage = client.get("/media-coverage").json()
        assert coverage == {
            "total": 1,
            "illustrated": 1,
            "missing": 0,
            "pending_exercises": 0,
            "sources": {"everkinetic": 1},
        }
        for ext, mime, char in [
            ("png", "image/png", "a"),
            ("webp", "image/webp", "b"),
            ("jpg", "image/jpeg", "c"),
        ]:
            response = client.get("/media/assets/" + char * 64 + "." + ext)
            assert response.status_code == 200
            assert response.headers["content-type"] == mime
        assert client.get("/media/assets/" + "a" * 64 + ".svg").status_code == 404
        db.exercises.update_one(
            {"_id": target["_id"]}, {"$set": {"overrides.equipment": "dumbbell"}}
        )
        assert (
            client.get("/media-coverage").json()["pending_exercises"] == 0
        )  # old content is stale
        queue_matches(db, rows, "repdb", "two", {"source_ref": "two", "links": []})
        # Explicit curated pending entry creates one current exercise to review.
        document = db.exercises.find_one()
        for ref in ["new-a", "new-b"]:
            db.media_matches.insert_one(
                {
                    "_id": ref,
                    "exercise_id": document["_id"],
                    "target_hash": effective_hash(document),
                    "status": "pending",
                }
            )
        coverage = client.get("/media-coverage").json()
        assert coverage["illustrated"] == 0
        assert coverage["pending_exercises"] == 1  # counts exercises, not duplicate proposals
