from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/wow_progress"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Blizzard
    BLIZZARD_CLIENT_ID: str = ""
    BLIZZARD_CLIENT_SECRET: str = ""
    BLIZZARD_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    BLIZZARD_REGION: str = "eu"

    # CORS – accepte soit un JSON array soit une string séparée par des virgules
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    # Frontend — URL de redirection après le callback OAuth
    FRONTEND_URL: str = "http://localhost:5173"

    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",")]
        return v


settings = Settings()
