"""Central settings, loaded from environment / .env. Nothing else in the app
should call os.environ directly — see BUILD_SPEC guardrail #5 (no secrets
scattered through source)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    public_base_url: str = "http://localhost:8000"
    env: str = "development"

    mongodb_uri: str = ""
    mongodb_db: str = "elevator_rf_survey"
    mongodb_tls: bool = True  # Atlas requires TLS; local/dev Mongo (docker, no srv) usually doesn't

    jwt_secret: str = ""
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    file_storage_backend: str = "local"     # local | s3
    file_storage_root: str = ""

    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = ""

    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
