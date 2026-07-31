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

    # Embedding
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-ada-002"

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

    # External tool APIs (optional; leave empty to use mock data)
    order_api_url: str = ""
    payment_api_url: str = ""
    logistics_api_url: str = ""


settings = Settings()
