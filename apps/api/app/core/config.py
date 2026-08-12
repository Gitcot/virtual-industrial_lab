from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration centrale de l'application, chargée depuis .env"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql://vil_user:changeme@db:5432/vil"
    secret_key: str = "changeme-generate-a-real-secret"
    access_token_expire_minutes: int = 60 * 24  # 24h
    algorithm: str = "HS256"


settings = Settings()
