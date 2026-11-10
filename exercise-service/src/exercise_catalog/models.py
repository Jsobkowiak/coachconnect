import hashlib
import json
import re
import unicodedata
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Muscle(StrEnum):
    ABDOMINALS = "abdominals"
    ABDUCTORS = "abductors"
    ADDUCTORS = "adductors"
    BICEPS = "biceps"
    CALVES = "calves"
    CHEST = "chest"
    FOREARMS = "forearms"
    GLUTES = "glutes"
    HAMSTRINGS = "hamstrings"
    LATS = "lats"
    LOWER_BACK = "lower_back"
    MIDDLE_BACK = "middle_back"
    NECK = "neck"
    QUADRICEPS = "quadriceps"
    SHOULDERS = "shoulders"
    TRAPS = "traps"
    TRICEPS = "triceps"


class Equipment(StrEnum):
    MEDICINE_BALL = "medicine_ball"
    DUMBBELL = "dumbbell"
    BODYWEIGHT = "bodyweight"
    BANDS = "bands"
    KETTLEBELLS = "kettlebells"
    FOAM_ROLL = "foam_roll"
    CABLE = "cable"
    MACHINE = "machine"
    BARBELL = "barbell"
    EXERCISE_BALL = "exercise_ball"
    EZ_CURL_BAR = "ez_curl_bar"
    OTHER = "other"


class ExerciseData(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=250)
    language: Literal["en", "fr"] = "en"
    aliases: list[str] = Field(default_factory=list)
    category: Literal[
        "powerlifting",
        "strength",
        "stretching",
        "cardio",
        "olympic_weightlifting",
        "strongman",
        "plyometrics",
    ]
    equipment: Equipment | None
    primary_muscles: list[Muscle] = Field(min_length=1)
    secondary_muscles: list[Muscle] = Field(default_factory=list)
    instructions: list[str] = Field(min_length=1)
    level: Literal["beginner", "intermediate", "expert"]
    force: Literal["static", "pull", "push"] | None
    mechanic: Literal["isolation", "compound"] | None

    @field_validator("instructions", "aliases")
    @classmethod
    def clean_strings(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("Empty instructions or aliases are not allowed")
        return list(dict.fromkeys(cleaned))

    @field_validator("primary_muscles", "secondary_muscles")
    @classmethod
    def unique_muscles(cls, values: list[Muscle]) -> list[Muscle]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def distinct_muscles(self):
        if set(self.primary_muscles) & set(self.secondary_muscles):
            raise ValueError("A muscle cannot be both primary and secondary")
        return self

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()


def normalized_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).casefold()
    return re.sub(
        r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c))
    ).strip()
