from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SOURCE_REF = "f00c92c7dcf1216a928a52c3706c7ce8e2f71ed5"
SOURCE_NAME = "free-exercise-db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CATALOG_", extra="ignore")

    mongo_uri: SecretStr
    database: str = "coachconnect_exercises"
    raw_directory: Path = Path("../.local/catalog/raw")
    media_directory: Path = Path("../.local/catalog/media")


def settings() -> Settings:
    return Settings()
