from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = Field(min_length=32)
    database_url: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
