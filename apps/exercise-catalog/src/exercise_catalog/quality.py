from difflib import SequenceMatcher

from exercise_catalog.models import ExerciseData, normalized_name


def duplicate_candidates(data: ExerciseData, source_key: str, existing: list[dict]) -> list[str]:
    """Suggest matches; never automatically collapse two different source IDs."""
    name = normalized_name(data.name)
    matches = []
    for other in existing:
        if other["source_key"] == source_key:
            continue
        stored = other["source_data"]
        if stored["equipment"] != data.equipment or stored["category"] != data.category:
            continue
        candidate = other["normalized_name"]
        if candidate == name or SequenceMatcher(None, name, candidate).ratio() >= 0.94:
            matches.append(other["_id"])
    return matches
