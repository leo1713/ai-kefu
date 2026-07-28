from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "ai-cs-api"
    debug: bool = False
    secret_key: str = "changeme-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_cs"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Claude
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # Encryption key for storing sensitive data (Fernet)
    encryption_key: str = ""

    # WeCom
    wecom_corp_id: str = ""
    wecom_agent_id: str = ""
    wecom_secret: str = ""
    wecom_token: str = ""
    wecom_encoding_aes_key: str = ""


settings = Settings()
