from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./llm_regression.db"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    slack_webhook_url: str | None = None
    teams_webhook_url: str | None = None
    redaction_patterns: str = r"(?i)(sk-[A-Za-z0-9_-]+|Bearer\s+[A-Za-z0-9._-]+)"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
