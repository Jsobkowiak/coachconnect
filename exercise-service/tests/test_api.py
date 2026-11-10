import pytest
from fastapi.testclient import TestClient

from exercise_catalog import api
from exercise_catalog.pipeline import process_records

pytestmark = pytest.mark.integration


def test_api_reads_corrected_fields_and_validates_filters(database, record, metadata, monkeypatch):
    db, config = database
    process_records(db, [record], metadata, "test")
    document = db.exercises.find_one()
    db.exercises.update_one({"_id": document["_id"]}, {"$set": {"overrides.name": "Mon squat"}})
    monkeypatch.setattr(api, "settings", lambda: config)
    with TestClient(api.app) as client:
        assert client.get("/health").status_code == 200
        result = client.get("/exercises", params={"q": "Mon squat", "equipment": "barbell"}).json()
        assert result["total"] == 1
        assert result["items"][0]["name"] == "Mon squat"
        assert client.get("/exercises", params={"q": "Barbell"}).json()["total"] == 0
        assert client.get("/exercises", params={"limit": 1000}).status_code == 422
        assert client.get("/exercises", params={"equipment": "invented"}).status_code == 422
        assert client.get("/exercises/unknown").status_code == 404
        assert client.get(f"/exercises/{document['_id']}").json()["name"] == "Mon squat"


def test_quality_inspection_and_review_history(database, record, metadata, monkeypatch):
    from exercise_catalog.review import decide

    db, config = database
    process_records(db, [{**record, "equipment": None}], metadata, "test")
    issue = db.quality_issues.find_one()
    decide(db, issue["_id"], "acknowledge", "Jonathan", "Equipment not documented")
    monkeypatch.setattr(api, "settings", lambda: config)
    with TestClient(api.app) as client:
        context = client.get(f"/quality-issues/{issue['_id']}").json()
        assert context["raw"]["payload"]["equipment"] is None
        assert context["issue"]["status"] == "resolved"
        assert client.get("/quality-issues/unknown").status_code == 404
        history = client.get("/quality-reviews").json()
        assert history["total"] == 1
        assert history["items"][0]["reviewer"] == "Jonathan"
        assert client.post("/quality-reviews", json={}).status_code == 405
