import base64

import pytest
from fastapi.testclient import TestClient

from exercise_catalog import api
from exercise_catalog.media import (
    SOURCE_REF,
    approve_match,
    effective_hash,
    queue_matches,
    reject_match,
    validate_png,
)
from exercise_catalog.pipeline import process_records

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aQ0cAAAAASUVORK5CYII="
)


def test_png_limits_and_format():
    assert validate_png(PNG) == (1, 1)
    for payload in [b'<svg onload="alert(1)"/>', b"GIF89a", PNG * 40_000]:
        with pytest.raises(ValueError):
            validate_png(payload)


@pytest.mark.integration
def test_explicit_matching_replay_staleness_and_asset_serving(
    database, record, metadata, monkeypatch, tmp_path
):
    db, config = database
    config.media_directory = tmp_path
    process_records(db, [record], metadata, "first")
    source = {"id": "0122", "title": "Barbell Squat", "png": ["png/0122-relaxation.png"]}
    summary = queue_matches(db, [source])
    assert summary["approved"] == 0  # Even exact names do not authorize publication.
    assert summary["pending"] == 1
    assert db.exercises.find_one().get("media") is None
    queue_matches(db, [source])
    assert db.media_matches.count_documents({}) == 1
    issue = db.media_matches.find_one()
    filename = "a" * 64 + ".png"
    db.media_sources.insert_one(
        {
            "_id": "source",
            "source_ref": SOURCE_REF,
            "source_id": "0122",
            "title": "Barbell Squat",
            "images": [{"filename": filename, "url": "/media/assets/" + filename}],
            "license": {"name": "CC BY-SA 4.0"},
        }
    )
    with pytest.raises(ValueError, match="proposed"):
        approve_match(db, issue["_id"], "9999", "Reviewer", "reason")
    with pytest.raises(ValueError, match="required"):
        approve_match(db, issue["_id"], "0122", "", "reason")
    approve_match(db, issue["_id"], "0122", "Reviewer", "Exercise and variant compared")
    with pytest.raises(ValueError, match="reviewed"):
        approve_match(db, issue["_id"], "0122", "Reviewer", "reason")
    assert queue_matches(db, [source])["approved"] == 1
    (tmp_path / filename).write_bytes(PNG)
    monkeypatch.setattr(api, "settings", lambda: config)
    with TestClient(api.app) as client:
        exercise = db.exercises.find_one()
        assert client.get("/exercises?with_media=true").json()["total"] == 1
        assert client.get("/exercises?with_media=false").json()["total"] == 0
        response = client.get("/media/assets/" + filename)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert client.get("/media/assets/not-a-hash.png").status_code == 404
        assert client.get("/media-matches?status=approved").json()["total"] == 1
        # A manual change invalidates the association without erasing its audit history.
        db.exercises.update_one(
            {"_id": exercise["_id"]}, {"$set": {"overrides.equipment": "dumbbell"}}
        )
        assert client.get("/exercises/" + exercise["_id"]).json()["media"] is None
        assert client.get("/exercises?with_media=true").json()["total"] == 0
        assert db.media_matches.find_one()["status"] == "approved"
        assert effective_hash(db.exercises.find_one()) != issue["target_hash"]
        queue_matches(db, [source])
        pending = db.media_matches.find_one({"status": "pending"})
        reject_match(db, pending["_id"], "Reviewer", "Wrong equipment")
        queue_matches(db, [source])
        assert db.media_matches.count_documents({"status": "pending"}) == 0
        assert db.media_matches.count_documents({"status": "rejected"}) == 1
        with pytest.raises(ValueError, match="reviewed"):
            approve_match(db, pending["_id"], "0122", "Reviewer", "reason")
