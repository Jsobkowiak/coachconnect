import pytest
from pydantic import ValidationError

from exercise_catalog.models import normalized_name
from exercise_catalog.quality import duplicate_candidates
from exercise_catalog.sources.free_exercise_db import extract, transform


def test_mapping_normalization_and_media_exclusion(record):
    record.update(
        equipment="e-z curl bar",
        category="olympic weightlifting",
        primaryMuscles=["lower back", "lower back"],
        images=["unverified.jpg"],
    )
    data = transform(record)
    assert data.equipment == "ez_curl_bar"
    assert data.category == "olympic_weightlifting"
    assert data.primary_muscles == ["lower_back"]
    assert "images" not in data.model_dump()
    assert normalized_name("  Développé-Couché! ") == "developpe couche"


@pytest.mark.parametrize(
    "changes",
    [
        {"id": None},
        {"name": " "},
        {"equipment": "invented"},
        {"primaryMuscles": []},
        {"primaryMuscles": ["invented"]},
        {"instructions": [" "]},
        {"level": "invented"},
        {"secondaryMuscles": ["quadriceps"]},
    ],
)
def test_bad_records_are_rejected(record, changes):
    with pytest.raises((ValidationError, ValueError)):
        transform({**record, **changes})


def test_unknown_equipment_is_not_invented(record):
    assert transform({**record, "equipment": None}).equipment is None


def test_variants_are_not_automatically_merged(record):
    data = transform(record)
    other = {
        "_id": "front",
        "source_key": "other:front",
        "normalized_name": "front squat",
        "source_data": data.model_dump(mode="json"),
    }
    assert not duplicate_candidates(data, "source:squat", [other])
    other["normalized_name"] = normalized_name(data.name)
    assert duplicate_candidates(data, "source:squat", [other]) == ["front"]


def test_source_requires_pinned_commit(tmp_path):
    with pytest.raises(ValueError, match="immutable"):
        extract("main", tmp_path)
